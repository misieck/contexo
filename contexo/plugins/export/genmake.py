#!/usr/bin/python
###############################################################################
#                                                                             
#   genmake.py
#   Component of Contexo commandline tools - (c) Scalado AB 2010
#                                                                             
#   Author: Ulf Holmstedt (ulf.holmstedt@scalado.com)
#           Thomas Eriksson (thomas.eriksson@scalado.com)
#                                                                             
#   ------------
#                                                                             
#   Generate GNU Makefile from contexo sources
#                                                                             
###############################################################################
#
# Paul's Rules of Makefiles (from: http://mad-scientist.net/make/rules.html)
#
# 1. Use GNU make.
#    Don't hassle with writing portable makefiles, use a portable make instead!
#
# 2. Every non-.PHONY rule must update a file with the exact name of its target.
#    Make sure every command script touches the file "$@"-- not "../$@", or "$(notdir $@)", but exactly $@. That way you and GNU make always agree.
#
# 3. Life is simplest if the targets are built in the current working directory.
#    Use VPATH to locate the sources from the objects directory, not to locate the objects from the sources directory.
#
# 4. Follow the Principle of Least Repetition.
# Try to never write a filename more than once. Do this through a combination of make variables, pattern rules, automatic variables, and GNU make functions.
# 
# 5. Every non-continued line that starts with a TAB is part of a command script--and vice versa.
# If a non-continued line does not begin with a TAB character, it is never part of a command script: it is always interpreted as makefile syntax. If a non-continued line does begin with a TAB character, it is always part of a command script: it is never interpreted as makefile syntax.
# 
# Continued lines are always of the same type as their predecessor, regardless of what characters they start with.

from argparse import ArgumentParser
import os
import contexo.ctx_export as ctx_export
import contexo.ctx_common as ctx_common
import contexo.ctx_sysinfo as ctx_sysinfo
from contexo.ctx_common import infoMessage, userErrorExit, warningMessage
import contexo.ctx_cfg as ctx_cfg
import contexo.ctx_cmod

#------------------------------------------------------------------------------
def create_module_mapping_from_module_list( ctx_module_list, depMgr):
    code_module_map = list()
    print 'mapping'
    for mod in ctx_module_list:
        #srcFiles = list()
        privHdrs = list()
        pubHdrs  = list()
        depHdrDirs = set()
        depHdrs = set()

        rawMod = ctx_module_list[mod] #ctx_cmod.CTXRawCodeModule( mod )

        srcs = rawMod.getSourceAbsolutePaths()
        privHdrs= rawMod.getPrivHeaderAbsolutePaths()
        pubHdrs = rawMod.getPubHeaderAbsolutePaths()
        testSrcs = rawMod.getTestSourceAbsolutePaths()
        testHdrs = rawMod.getTestHeaderAbsolutePaths()
        modName = rawMod.getName()
        ## moduleDependencies[] only includes the top level includes, we must recurse through those to get all dependencies
        for hdr in  depMgr.moduleDependencies[modName]:
            hdr_location = depMgr.locate(hdr)
            if hdr_location != None:
                hdrpaths = depMgr.getDependencies(hdr_location)
                for hdrpath in hdrpaths:
					depHdrs.add( hdrpath)

        modDict = { 'MODNAME': rawMod.getName(), 'SOURCES': srcs, 'PRIVHDRS': privHdrs, 'PUBHDRS': pubHdrs, 'PRIVHDRDIR': rawMod.getPrivHeaderDir(), 'TESTSOURCES':testSrcs , 'TESTHDRS':testHdrs, 'DEPHDRS':depHdrs, 'TESTDIR':rawMod.getTestDir()}
        code_module_map.append( modDict )


    return code_module_map


#------------------------------------------------------------------------------
#-- End of method declaration
#------------------------------------------------------------------------------


msgSender = 'Makefile Export'

contexo_config_path = os.path.join( ctx_common.getUserCfgDir(), ctx_sysinfo.CTX_CONFIG_FILENAME )
infoMessage("Using config file '%s'"%contexo_config_path,  1)
cfgFile = ctx_cfg.CFGFile(contexo_config_path)
ctx_common.setInfoMessageVerboseLevel( int(cfgFile.getVerboseLevel()) )

infoMessage("Receiving export data from Contexo...", 1)
package = ctx_export.CTXExportData()
package.receive() # Reads pickled export data from stdin

for item in package.export_data.keys():
    infoMessage("%s: %s"%(item, str(package.export_data[item])))

# Retrieve build config from session
bc_file = package.export_data['SESSION'].getBCFile()
build_params = bc_file.getBuildParams()

depRoots = package.export_data['PATHS']['MODULES']
incPaths = list()
for depRoot in depRoots:
    incPathCandidates = os.listdir( depRoot )

    for cand in incPathCandidates:
        path = os.path.join(depRoot, cand)
        if contexo.ctx_cmod.isContexoCodeModule( path ):
            incPaths.append( path )
            
depMgr = package.export_data['DEPMGR']
module_map = create_module_mapping_from_module_list( package.export_data['MODULES'], depMgr)

# Start writing to the file - using default settings for now
makefile = open("Makefile", 'w')

# File header
makefile.write("#############################################\n")
makefile.write("### Makefile generated with contexo plugin.\n")

# Standard compiler settings
makefile.write("CC=gcc\n")
makefile.write("CFLAGS="+build_params.cflags+"\n")
makefile.write("LDFLAGS=\n")
makefile.write("OBJ_TEMP=.\n")
makefile.write("\n")
makefile.write("AR=ar\n")
makefile.write("RANLIB=ranlib\n")
makefile.write("LIB_OUTPUT=output/lib\n")
makefile.write("\n")
makefile.write("EXPORT_CMD=cp\n")
makefile.write("HEADER_OUTPUT=output/inc\n")
makefile.write("\n")
makefile.write("EXECUTABLE=hello\n")
makefile.write("\n")

# Preprocessor defines
makefile.write("### Standard defines\n");
makefile.write("PREP_DEFS=")
for prepDefine in build_params.prepDefines:
	makefile.write("-D"+prepDefine+" ")
makefile.write("\n")

# "all" definition
makefile.write("\n")
makefile.write("### Build-all definition\n")
makefile.write("all: ")
for comp in package.export_data['COMPONENTS']:
	for lib in comp.libraries:
		libfilename=lib+".a"
		makefile.write(libfilename+" ")
makefile.write("\n")
makefile.write("\n")
makefile.write("clean:\n")
makefile.write("\trm -f $(OBJ_TEMP)/*.o\n")
makefile.write("\trm -f $(LIB_OUTPUT)/*.a\n")
makefile.write("\trm -f $(HEADER_OUTPUT)/*.h\n")
makefile.write("\n")

modules = package.export_data['MODULES']

headerDict = dict()
for modName in modules:
	module = modules[modName]
	files = module.getPubHeaderAbsolutePaths()
	for f in files:
		headerDict[os.path.basename(f)] = f


# component definitions
makefile.write("\n")
makefile.write("### Component definitions\n")
for comp in package.export_data['COMPONENTS']:
	headerFiles=list()
	for headerFile in comp.publicHeaders:
		headerFiles.append(headerFile)

	for lib in comp.libraries:
		objectfiles=list()
		libfilename=lib+".a"

		for libs in comp.libraries[lib]:
			for srcFile in modules[libs].getSourceFilenames():
				objectfiles.append(srcFile[:-2]+".o ")
			for testFile in modules[libs].getTestSourceFilenames():
				objectfiles.append(testFile[:-2]+".o ")

		makefile.write(libfilename+": ")
		for objfile in objectfiles:
			makefile.write(objfile+" ")
		makefile.write("\n")

		makefile.write("\t$(AR) r $@ ")
		for objfile in objectfiles:
			makefile.write("$(OBJ_TEMP)/"+objfile+" ")
		makefile.write("\n")

		makefile.write("\t$(RANLIB) $@\n")

	for headerFile in headerFiles:
		makefile.write("\t$(EXPORT_CMD) "+headerDict[headerFile]+" $(HEADER_OUTPUT)/"+headerFile+"\n")
	makefile.write("\n")

makefile.write("\n")
makefile.write("### Object definitions\n")

for mod in module_map:
	for srcFile in mod['SOURCES']:
		objfile = os.path.basename(srcFile)[:-2]+".o"
		
		makefile.write(objfile + ": " + srcFile)
		for hdr in mod['DEPHDRS']:
			makefile.write(" " + hdr)
		makefile.write("\n")
		makefile.write("\t$(CC) $(CFLAGS) ")
		for hdrdir in mod['DEPHDRS']:
			makefile.write(" -I"+os.path.dirname( hdrdir))
		makefile.write(" $(PREP_DEFS) -c "+srcFile+" -o $@\n");

	for testFile in mod['TESTSOURCES']:
		objfile = os.path.basename(testFile)[:-2]+".o"
		privInclude = module.getName().upper()+"_PRIV"
		
		makefile.write(objfile + ": " + testFile + " ")
		for hdr in mod['DEPHDRS']:
			makefile.write( " " + hdr)
		makefile.write("\n")
		makefile.write("\t$(CC) $(CFLAGS) ")
		for hdrdir in mod['DEPHDRS']:
			makefile.write(" -I"+os.path.dirname( hdrdir))
		makefile.write("$(PREP_DEFS)")
		for hdrdir in mod['DEPHDRS']:
			makefile.write(" -I"+os.path.dirname( hdrdir))
		makefile.write(" -I"+module.getRootPath()+"/test/ -c "+testFile+" -o $@\n")
makefile.write("### End of Makefile\n")
makefile.write("\n")

makefile.close()
