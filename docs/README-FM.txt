To compile against a set of mods:

1. Bootstrap MCP with jars, and run decompile and reobfuscate.
   -- Forge should also work for this, provided it uses MCP's temp/ directory
      (and I think it does)
2. Run both scripts once to create their directories:
$ python runtime/deobfuscate_libs.py
$ python runtime/recompile_mods.py
3. Add your mod dependencies to lib-obf/
4. Run deobfuscate_libs to create the files to build against:
$ python runtime/deobfuscate_libs.py
5. Create a project in mods/ to hold your source:
$ mkdir -p mods/your_mod/src/{common,client,server}
   -- Not sure how the client/server split interacts with integrated forge yet.
6. Add your source to the appropriate directories.  You can also have a
   mods/your_mod/resources/ directory for other things that go in the .zip files
   (this uses the same common/client/server split as src/)
7. Compile with recompile_mods.py:
$ python runtime/recompile_mods.py
8. Your finished .zip files should be in packages/
