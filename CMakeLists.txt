cmake_minimum_required(VERSION 3.13)

project(FlutterbugVMs
    VERSION 0.1.0
    LANGUAGES C CXX)

if(NOT CMAKE_BUILD_TYPE)
    set(CMAKE_BUILD_TYPE Release)
endif()

set(EMGLKEN_ROOT ${CMAKE_CURRENT_SOURCE_DIR}/emglken)

if(${CMAKE_BUILD_TYPE} STREQUAL Release)
    set(REMGLK_RS_LIB_FOLDER ${EMGLKEN_ROOT}/target/release)
else()
    set(REMGLK_RS_LIB_FOLDER ${EMGLKEN_ROOT}/target/debug)
endif()

# Static lib filename differs by toolchain: libremglk_capi.a on Unix,
# remglk_capi.lib on MSVC. CMAKE_STATIC_LIBRARY_PREFIX/SUFFIX gives the
# right pair for the host toolchain.
set(REMGLK_RS_LIB
    ${REMGLK_RS_LIB_FOLDER}/${CMAKE_STATIC_LIBRARY_PREFIX}remglk_capi${CMAKE_STATIC_LIBRARY_SUFFIX})
set(GLK_HEADERS ${EMGLKEN_ROOT}/remglk/remglk_capi/src/glk)

function(add_sources target dir)
    cmake_parse_arguments(PARSE_ARGV 2 ADD "" "" "SRCS")
    list(TRANSFORM ADD_SRCS PREPEND ${dir})
    target_sources(${target} PRIVATE ${ADD_SRCS})
    target_include_directories(${target} PRIVATE ${dir})
endfunction()

add_library(emglken_native_shims STATIC native_shims.c)

function(emglken_native_vm target)
    set_target_properties(${target} PROPERTIES LINKER_LANGUAGE CXX)
    target_include_directories(${target} PRIVATE ${GLK_HEADERS})
    target_link_libraries(${target} PRIVATE ${REMGLK_RS_LIB} emglken_native_shims)
    if(APPLE)
        target_link_libraries(${target} PRIVATE
            "-framework CoreFoundation"
            "-framework Security"
            pthread dl m)
    elseif(WIN32)
        # System libraries the Rust standard library expects on MSVC.
        target_link_libraries(${target} PRIVATE
            ws2_32 userenv ntdll bcrypt advapi32 kernel32 user32)
    else()
        target_link_libraries(${target} PRIVATE pthread dl m)
    endif()
endfunction()

add_executable(glulxe)
add_sources(glulxe "${EMGLKEN_ROOT}/glulxe/"
    SRCS accel.c debugger.c exec.c files.c float.c funcs.c
    gestalt.c glkop.c heap.c main.c operand.c osdepend.c profile.c
    search.c serial.c string.c vm.c unixstrt.c unixautosave.c)
emglken_native_vm(glulxe)
target_compile_definitions(glulxe PRIVATE OS_UNIX)
if(NOT MSVC)
    target_compile_options(glulxe PRIVATE -Wall -Wmissing-prototypes -Wno-unused)
endif()

function(bocfel_common target)
    add_sources(${target} "${EMGLKEN_ROOT}/garglk/terps/bocfel/"
        SRCS blorb.cpp branch.cpp dict.cpp glkautosave.cpp glkstart.cpp iff.cpp
        io.cpp mathop.cpp meta.cpp memory.cpp objects.cpp options.cpp osdep.cpp
        patches.cpp process.cpp random.cpp screen.cpp sound.cpp stack.cpp stash.cpp
        unicode.cpp util.cpp zterp.cpp)
    emglken_native_vm(${target})
    set_property(TARGET ${target} PROPERTY CXX_STANDARD 14)
    target_compile_definitions(${target} PRIVATE ZTERP_GLK ZTERP_GLK_BLORB
        ZTERP_GLK_NO_STDIO ZTERP_GLK_UNIX ZTERP_NO_OPTIONS
        "ZTERP_STATIC_PATCH_FILE=\"static-patches.h\"")
    if(NOT MSVC)
        # MSVC enables C++ exceptions through /EHsc by default.
        target_compile_options(${target} PRIVATE -Wall -fexceptions)
    endif()
endfunction()

add_executable(bocfel-noz6)
bocfel_common(bocfel-noz6)
target_compile_definitions(bocfel-noz6 PRIVATE ZTERP_NO_V6)

add_executable(bocfel)
bocfel_common(bocfel)

add_executable(git)
add_sources(git "${EMGLKEN_ROOT}/git/"
    SRCS accel.c compiler.c gestalt.c git.c glkop.c heap.c
    memory.c opcodes.c operands.c peephole.c savefile.c saveundo.c
    search.c terp.c git_unix.c)
emglken_native_vm(git)
if(MSVC)
    # USE_DIRECT_THREADING relies on GCC's labels-as-values extension.
    # Drop on MSVC; git's switch-based dispatch is the fallback.
    target_compile_definitions(git PRIVATE USE_INLINE)
else()
    target_compile_definitions(git PRIVATE USE_DIRECT_THREADING USE_INLINE)
    target_compile_options(git PRIVATE -Wall -Wno-int-conversion -Wno-pointer-sign -Wno-unused-but-set-variable)
endif()

add_executable(hugo)
add_sources(hugo "${EMGLKEN_ROOT}/hugo/source/"
    SRCS he.c heexpr.c hemisc.c heobject.c heparse.c heres.c herun.c heset.c stringfn.c)
add_sources(hugo "${EMGLKEN_ROOT}/hugo/heglk/"
    SRCS heglk.c heglkunix.c)
emglken_native_vm(hugo)
target_compile_definitions(hugo PRIVATE COMPILE_V25 GLK NO_KEYPRESS_CURSOR "HUGO_INLINE=static inline")
if(NOT MSVC)
    target_compile_options(hugo PRIVATE -Wall -Wno-unused-but-set-variable)
endif()

find_package(ZLIB)
if(ZLIB_FOUND)
    add_executable(scare)
    add_sources(scare "${EMGLKEN_ROOT}/garglk/terps/scare/"
        SRCS os_glk.c scdebug.c scevents.c scexpr.c scgamest.c scinterf.c sclibrar.c
        sclocale.c scmemos.c scnpcs.c scobjcts.c scparser.c scprintf.c scprops.c
        scresour.c screstrs.c scrunner.c scserial.c sctaffil.c sctafpar.c sctasks.c
        scutils.c scvars.c)
    emglken_native_vm(scare)
    target_link_libraries(scare PRIVATE ZLIB::ZLIB)
endif()

add_executable(tads)
add_sources(tads "${EMGLKEN_ROOT}/tads/glk/"
    SRCS memicmp.c osbuffer.c osemglken.c osextra.c osglk.c osglkban.c osmisc.c osparse.c
    osportable.cc t23run.cpp t2askf.c t2indlg.c t3askf.cpp t3indlg.cpp vmuni_cs.cpp)
add_sources(tads "${EMGLKEN_ROOT}/tads/tads2/"
    SRCS argize.c bif.c bifgdum.c cmap.c cmd.c dat.c dbgtr.c errmsg.c execmd.c
    fio.c fioxor.c getstr.c ler.c linfdum.c lst.c mch.c mcm.c mcs.c obj.c oem.c
    os0.c oserr.c osifc.c osnoui.c osrestad.c osstzprs.c ostzposix.c out.c output.c
    ply.c qas.c regex.c run.c runstat.c suprun.c trd.c voc.c vocab.c)
add_sources(tads "${EMGLKEN_ROOT}/tads/tads3/"
    SRCS charmap.cpp md5.cpp resldexe.cpp resload.cpp sha2.cpp std.cpp tcerr.cpp
    tcerrmsg.cpp tcgen.cpp tcglob.cpp tcmain.cpp tcprs.cpp tcprs_rt.cpp tcprsnf.cpp
    tcprsnl.cpp tcprsstm.cpp tcsrc.cpp tct3.cpp tct3_d.cpp tct3nl.cpp tct3stm.cpp
    tct3unas.cpp tctok.cpp utf8.cpp vmanonfn.cpp vmbif.cpp vmbifl.cpp vmbifreg.cpp
    vmbift3.cpp vmbiftad.cpp vmbiftio.cpp vmbignum.cpp vmbignumlib.cpp vmbt3_nd.cpp
    vmbytarr.cpp vmcfgmem.cpp vmcoll.cpp vmconhmp.cpp vmconsol.cpp vmcrc.cpp
    vmcset.cpp vmdate.cpp vmdict.cpp vmdynfunc.cpp vmerr.cpp vmerrmsg.cpp
    vmfile.cpp vmfilnam.cpp vmfilobj.cpp vmfref.cpp vmfunc.cpp vmglob.cpp
    vmgram.cpp vmhash.cpp vmhostsi.cpp vmhosttx.cpp vmimage.cpp vmimg_nd.cpp
    vmini_nd.cpp vminit.cpp vminitim.cpp vmintcls.cpp vmisaac.cpp vmiter.cpp
    vmlog.cpp vmlookup.cpp vmlst.cpp vmmain.cpp vmmcreg.cpp vmmeta.cpp
    vmnetfillcl.cpp vmobj.cpp vmop.cpp vmpack.cpp vmpat.cpp vmpool.cpp
    vmpoolim.cpp vmregex.cpp vmrun.cpp vmrunsym.cpp vmsa.cpp vmsave.cpp vmsort.cpp
    vmsortv.cpp vmsrcf.cpp vmstack.cpp vmstr.cpp vmstrbuf.cpp vmstrcmp.cpp
    vmtmpfil.cpp vmtobj.cpp vmtype.cpp vmtypedh.cpp vmtz.cpp vmtzobj.cpp
    vmundo.cpp vmvec.cpp vmconnom.cpp)
emglken_native_vm(tads)
set_property(TARGET tads PROPERTY CXX_STANDARD 11)
target_compile_definitions(tads PRIVATE EMGLKEN GLK GLK_TIMERS GLK_UNICODE NO_T2_COPYRIGHT_NOTICE
    OSNOUI_OMIT_OS_FPRINT OSNOUI_OMIT_OS_FPRINTZ RUNTIME TC_TARGET_T3 VMGLOB_STRUCT)
if(NOT MSVC)
    target_compile_options(tads PRIVATE -Wno-deprecated-register -Wno-logical-not-parentheses -Wno-pointer-sign -Wno-string-concatenation)
endif()
