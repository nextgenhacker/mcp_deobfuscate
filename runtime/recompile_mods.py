#!/usr/bin/env python
# mcp_rebuild - A Python script for safe and easy rebuilding of MCP projects.
# Copyright (c) 2011 FunnyMan3595 (Charlie Nolan)
# This code is made avilable under the MIT license.  See LICENSE for the full
# details.

import itertools, os, os.path, platform, shutil, subprocess, sys, tarfile, \
       zipfile, tempfile

# Convenience functions.  These make the settings settings easier to work with.
absolute = lambda rawpath: os.path.abspath(os.path.expanduser(rawpath))
relative = lambda relpath: absolute(os.path.join(BASE, relpath))
def make_if_needed(dir):
    if not os.path.exists(dir):
        os.makedirs(dir)
def clean_if_needed(dir):
    if os.path.exists(dir):
        shutil.rmtree(dir)
    os.makedirs(dir)

CLIENT, SERVER, FORGE = range(3)

BASE = absolute(".")
USER = relative("mods")
TEMP = relative("temp/mods")
LIB = relative("lib")
MCP_TEMP = relative("temp")
TARGET = relative("packages")

# Most of this script assumes it's in the MCP directory, so let's go there.
os.chdir(BASE)

# Create the project directory and force it to be seen as a category.
if not os.path.exists(USER):
    os.makedirs(USER)

    # Touch the CATEGORY file.
    with open(os.path.join(USER, "CATEGORY"), "w") as catfile:
        catfile.write("This is a placeholder file to mark this directory as a "
                      "category, not a project.")

# Create/clean the temp directory.
clean_if_needed(TEMP)

# Create/clean the package directory.
clean_if_needed(TARGET)

# JAR files to build against.
DEOBF_CLIENT = relative("temp/minecraft_exc.jar")
DEOBF_SERVER = relative("temp/minecraft_server_exc.jar")

# MCP's bin directory, the directory MCP will obfuscate from.
MCP_BIN = relative("bin")
# The obvious subdirectories.
MCP_BIN_CLIENT = os.path.join(MCP_BIN, "minecraft")
MCP_BIN_SERVER = os.path.join(MCP_BIN, "minecraft_server")

# MCP's reobf directory, the directory MCP will place reobfuscated classes in.
MCP_REOBF = relative("reobf")
# The obvious subdirectories.
MCP_REOBF_CLIENT = os.path.join(MCP_REOBF, "minecraft")
MCP_REOBF_SERVER = os.path.join(MCP_REOBF, "minecraft_server")

# This class is used to represent a user project, also known as a subdirectory
# of USER.  The format is described in the README.
class Project(object):
    def __init__(self, directory):
        self.dir = directory

        self.name = self.get_config("PROJECT_NAME") \
                    or os.path.basename(directory)
        self.version = self.get_config("VERSION")
        self.package_name = self.get_config("PACKAGE_NAME")
        self.hide_source = self.get_config("HIDE_SOURCE", is_boolean=True)
        self.package_command = self.get_config("PACKAGE_COMMAND")

    def get_config(self, setting, is_boolean=False):
        filename = os.path.join(self.dir, "conf", setting)
        exists = os.path.isfile(filename)

        if is_boolean:
            return exists
        elif not exists:
            return None
        else:
            return open(filename).read().strip()

    @staticmethod
    def collect_projects(root, projects):
        """Collects all the active projects under root into projects."""
        for (dir, subdirs, files) in os.walk(root, followlinks=True):
            if "DISABLED" in files:
                # This project or category has been disabled.  Skip it.
                del subdirs[:]
                print "Disabled project or category at %s." % dir
            elif "CATEGORY" in files:
                # This is a category, not a project.  Continue normally.
                pass
                print "Found category at %s, recursing." % dir
            else:
                # This is a project.  Create it, but do not continue into
                # subdirectories.
                projects.append(Project(dir))
                del subdirs[:]
                print "Found project at %s." % dir

    def copy_files(self, source, dest, failcode):
        for (source_dir, subdirs, files) in os.walk(source, followlinks=True):
            dest_dir = os.path.join(dest, os.path.relpath(source_dir, source))
            make_if_needed(dest_dir)

            for file in files:
                if file.startswith("."):
                    continue

                try:
                    shutil.copy2(os.path.join(source_dir, file), dest_dir)
                except shutil.WindowsError:
                    pass # Windows doesn't like copying access time.

            for i in range(len(subdirs), 0, -1):
                if subdirs[i-1].startswith("."):
                    del subdirs[i-1]

    def get_package_file(self, side):
        if self.package_name is not None:
            filename = self.package_name
        else:
            if self.version is not None:
                filename = "%s-%s" % (self.name, self.version)
            else:
                filename = "%s" % self.name

        if side == SERVER:
            filename += "-server"
        elif side == FORGE:
            filename += "-universal"

        filename += ".zip"

        return os.path.join(TEMP, filename)

    @staticmethod
    def collect_files(root, relative=False, required_extension=None):
        all_files = set()
        if not os.path.isdir(root):
            return all_files

        for (dir, subdirs, files) in os.walk(root, followlinks=True):
            for file in files:
                if file.startswith("."):
                    continue

                ext = os.path.splitext(file)[1].lower()
                if required_extension and ext != required_extension:
                    continue

                full_name = os.path.join(dir, file)
                if relative:
                    all_files.add(os.path.relpath(full_name, root))
                else:
                    all_files.add(full_name)

            for i in range(len(subdirs), 0, -1):
                if subdirs[i-1].startswith("."):
                    del subdirs[i-1]

        return all_files

    def zip(self, archive_name, files=None, clean=False):
        if not os.path.exists(archive_name):
            mode = "w"
        else:
            mode = "a"

        archive = zipfile.ZipFile(archive_name, mode)
        try:
            if files is None:
                for dir, subdirs, files in os.walk(".", followlinks=True):
                    for file in files:
                        archive.write(os.path.join(dir, file))
            else:
                for file in files:
                    archive.write(file)
        finally:
            archive.close()

    def compile(self, side, out_dir, library_classpath):
        source_dirs = [os.path.join(self.dir, "src", "common")]
        if side == CLIENT:
            source_dirs.append(os.path.join(self.dir, "src", "client"))
        elif side == SERVER:
            source_dirs.append(os.path.join(self.dir, "src", "server"))

        source_files = set()
        for dir in source_dirs:
            source_files.update(self.collect_files(dir, required_extension=".java"))

        if side in [CLIENT, FORGE]:
            classpath = MCP_BIN_CLIENT + ":" + library_classpath
        else: # if side == SERVER:
            classpath = MCP_BIN_SERVER + ":" + library_classpath

        command = ["javac", "-Xlint:all",
                   "-sourcepath", ":".join(source_dirs), "-classpath",
                   classpath, "-d", out_dir] + list(source_files)

        self.call_or_die(command)

    def obfuscate(self, side, stored_inheritance):
        classpath = "runtime/bin/jcommander-1.29.jar:runtime/bin/asm-all-3.3.1.jar:runtime/bin/mcp_deobfuscate-1.0.jar"
        main_class = "org.ldg.mcpd.MCPDeobfuscate"
        outdir = TARGET

        if side in [CLIENT, FORGE]:
            config = os.path.join(MCP_TEMP, "client_ro.srg")
            mc_jar = DEOBF_CLIENT
        else: #if side == SERVER:
            config = os.path.join(MCP_TEMP, "server_ro.srg")
            mc_jar = DEOBF_SERVER

        command = ["java", "-classpath", classpath, main_class,
                   "--stored_inheritance"] +  stored_inheritance + ["--invert",
                   "--config", config, "--outdir", outdir, "--indir", "/",
                   "--infiles", self.get_package_file(side)]

        print "---Obfuscating %s---" % self.name
        self.call_or_die(command)
        print "---Obfuscation complete---"
        print

    @staticmethod
    def call_or_die(cmd, shell=False):
        exit = subprocess.call(cmd, shell=shell)
        if exit != 0:
            print "Command failed: %s" % cmd
            print "Failed to package project %s.  Aborting." % project.name
            sys.exit(1)

    def package(self, side, in_dir):
        """Packages this project's files."""
        created = False
        package = self.get_package_file(side)
        if os.path.exists(package):
            # Ensure a clean start.  Should already be done by now, though.
            os.remove(package)

        # Side-specific directories
        if side == CLIENT:
            source = os.path.join(self.dir, "src", "client")
            resources = os.path.join(self.dir, "resources", "client")
        elif side == SERVER:
            source = os.path.join(self.dir, "src", "server")
            resources = os.path.join(self.dir, "resources", "server")

        if not self.hide_source:
            ## Collect and package source files.
            # Common first, so they can be overridden.
            common_source = os.path.join(self.dir, "src", "common")
            if os.path.isdir(common_source) and os.listdir(common_source):
                # To package these, we just change to the appropriate directory
                # and let self.zip command find everything in it.
                os.chdir(common_source)
                self.zip(package)
                created = True


            if side != FORGE and os.path.isdir(source) and os.listdir(source):
                os.chdir(source)
                self.zip(package)
                created = True

        ## Collect and package class files.
        if os.path.exists(in_dir) and os.listdir(in_dir):
            os.chdir(in_dir)
            self.zip(package)
            created = True


        ## Collect and package resource files.
        # Common first, so they can be overridden.
        common_resources = os.path.join(self.dir, "resources", "common")
        if os.path.isdir(common_resources):
            # To package these, we just change to the appropriate directory
            # and let the shell and zip command find everything in it.
            os.chdir(common_resources)
            self.zip(package)
            created = True

        if side != FORGE and os.path.isdir(resources):
            os.chdir(resources)
            self.zip(package)
            created = True

        os.chdir(BASE)
        return created

have_forge = os.path.exists(relative("src/common"))
if have_forge:
    print "!!! Forge detected.  Building universal packages only. !!!"
    print

projects = []
if not os.path.isdir(USER):
    print "No user directory found.  Nothing to do."
    sys.exit(0)
else:
    Project.collect_projects(USER, projects)

if os.path.exists(os.path.join(LIB, "minecraft.jar.inh")) \
   or os.path.exists(os.path.join(LIB, "minecraft_server.jar.inh")):
    pass # Yay!
else:
    print "Please run deobfuscate_libs first."
    sys.exit(1)

libraries = []
stored_inheritance = []
for filename in os.listdir(LIB):
    base, extension = os.path.splitext(filename)
    if extension.lower() == ".inh":
        stored_inheritance.append(os.path.join(LIB, filename))
    elif extension.lower() in [".jar", ".zip"]:
        libraries.append(os.path.join(LIB, filename))

library_classpath = ":".join(libraries)

count = 0
client_count = 0
server_count = 0
for project in projects:
    print "Processing %s..." % project.name
    any_created = False

    if have_forge:
        sides = [FORGE]
    else:
        sides = [CLIENT, SERVER]

    for side in sides:
        compile_dir = os.path.join(TEMP, project.name)
        if side == SERVER:
            compile_dir += "_server"
        elif side == FORGE:
            compile_dir += "_universal"

        clean_if_needed(compile_dir)

        project.compile(side, compile_dir, library_classpath)

        created = project.package(side, compile_dir)

        if created:
            any_created = True
            project.obfuscate(side, stored_inheritance)

            if side == CLIENT:
                client_count += 1
            elif side == SERVER:
                server_count += 1
    if any_created:
        count += 1

s = "" if count == 1 else "s"
print "%d project%s compiled and packaged successfully." % (count, s)
if count and not have_forge:
    print "(%d client, %d server)" % (client_count, server_count)
