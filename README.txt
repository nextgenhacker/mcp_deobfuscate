To compile a mod with mcp_deobfuscate and mcp_interface:

1. Bootstrap a new MCP install with jars, and run decompile and reobfuscate.
   -- Installing Forge also works, but don't forget to reobfuscate after!
2. Add mcp_deobfuscate.jar and its dependencies to runtime/bin/
   (see mcp_deobfuscate's README for more details)
3. Copy all of mcp_interface into the MCP directory.
4. Run both mcp_interface scripts once to create their directories:
   $ python runtime/deobfuscate_libs.py
   $ python runtime/recompile_mods.py
5. Add your mod's dependencies (if any) to lib-obf/
6. Run deobfuscate_libs to create the files to build against:
   $ python runtime/deobfuscate_libs.py
7. Create a project in mods/ to hold your source:
   $ mkdir -p mods/your_mod/src/{common,client,server}
   -- With Forge, you'll only want common; client and server will be ignored.
8. Add your source to the appropriate directories.  You can also have a
   mods/your_mod/resources/ directory for other things that go in the .zip files
   (This uses the same common/client/server split as src/, including the Forge
    caveat.)
9. Compile with recompile_mods.py:
   $ python runtime/recompile_mods.py
   -- Note the last line of output!  Mod source is included by default; you can
      touch mods/your_mod/conf/HIDE_SOURCE to remove it from future builds, but
      please consider leaving it in.
10. Your finished .zip files will be in packages/
