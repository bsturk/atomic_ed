@echo off
rem ANSI / CP437 artwork: keep literal ESC bytes and DOS CRLF line endings.
rem DOSBox-X has ANSI support; real MS-DOS needs ANSI.SYS for colors.
rem SELECT.BAT - MS-DOS 6.22 or DOSBox-X; run from the game directory.
rem Sources: SCENARIO\STALINGR, SCENARIO\CRUSADER, SCENARIO\V4V.
rem Requires the current INVADE-PATCHED.EXE with startup-selection support.
rem Interactive choices select the battle, launch INVADE and return here.
rem Arguments stage/check only. Native D-Day scenarios need no file copies.
rem Copies one complete DOS export to SCENARIO using a unique basename.
rem Existing staged copies of that same scenario are replaced.
if not exist INVADE.EXE goto noroot
if not exist DATA\PCWATW.REZ goto noroot
set WAWDIR=
set WAWSRC=
set WAWDST=
if "%1"=="" goto main
if "%2"=="" goto usage
if not "%3"=="" goto usage
if "%1"=="STALINGR" goto stargs
if "%1"=="CRUSADER" goto ocargs
if "%1"=="V4V" goto v4args
if "%1"=="DDAY" goto ddargs
goto usage

:main
echo [0;37;44m
cls
echo.
echo [0;36;44m  ษออออออออออออออออออออออออออออออออออออออออออออออออออออออออออออออออออออออออออป
echo [0;36;44m  บ                     [1;33mฑฑ  [1;37mW O R L D   A T   W A R[1;33m  ฑฑ                      [0;36;44mบ
echo [0;36;44m  บ              [0;37;44mA T O M I C   G A M E S   /   SCENARIO COMMAND              [0;36;44mบ
echo [0;36;44m  ฬออออออออออออออออออออออออออออออออออออออออออออออออออออออออออออออออออออออออออน
echo [0;36;44m  บ[1;33m  THEATER OF OPERATIONS                                                   [0;36;44mบ
echo [0;36;44m  บ[0;37;44m  Select a campaign, then choose your battle.                             [0;36;44mบ
echo [0;36;44m  บ                                                                          [0;36;44mบ
echo [0;36;44m  บ[0;37;44m  KEY   CAMPAIGN / THEATER                                                [0;36;44mบ
echo [0;36;44m  วฤฤฤฤฤฤฤฤฤฤฤฤฤฤฤฤฤฤฤฤฤฤฤฤฤฤฤฤฤฤฤฤฤฤฤฤฤฤฤฤฤฤฤฤฤฤฤฤฤฤฤฤฤฤฤฤฤฤฤฤฤฤฤฤฤฤฤฤฤฤฤฤฤฤถ
echo [0;36;44m  บ[1;33m  [1]   [1;31mSTALINGRAD                  [0;37;44mEastern Front                         [0;36;44mบ
echo [0;36;44m  บ                                                                          [0;36;44mบ
echo [0;36;44m  บ[1;33m  [2]   [1;33mOPERATION CRUSADER          [0;37;44mNorth Africa                          [0;36;44mบ
echo [0;36;44m  บ                                                                          [0;36;44mบ
echo [0;36;44m  บ[1;33m  [3]   [1;32mV FOR VICTORY               [0;37;44mFour battlesets                       [0;36;44mบ
echo [0;36;44m  บ                                                                          [0;36;44mบ
echo [0;36;44m  บ[1;33m  [4]   [1;36mD-DAY                       [0;37;44mAmerica Invades!                      [0;36;44mบ
echo [0;36;44m  บ                                                                          [0;36;44mบ
echo [0;36;44m  บ                                                                          [0;36;44mบ
echo [0;36;44m  บ                                                                          [0;36;44mบ
echo [0;36;44m  บ                                                                          [0;36;44mบ
echo [0;36;44m  บ[1;33m  [0]   [1;37mReturn to DOS[0;37;44m                  Press the highlighted key          [0;36;44mบ
echo [0;36;44m  ศออออออออออออออออออออออออออออออออออออออออออออออออออออออออออออออออออออออออออผ
choice /c:12340 /n "[1;33;44m    Select theater: [1;37m"
if errorlevel 255 goto nochoice
if errorlevel 5 goto done
if errorlevel 4 goto ddmenu
if errorlevel 3 goto v4menu
if errorlevel 2 goto ocmenu
if errorlevel 1 goto stmenu
goto nochoice

:ddmenu
echo [0;37;44m
cls
echo.
echo [0;36;44m  ษออออออออออออออออออออออออออออออออออออออออออออออออออออออออออออออออออออออออออป
echo [0;36;44m  บ                     [1;33mฑฑ  [1;37mW O R L D   A T   W A R[1;33m  ฑฑ                      [0;36;44mบ
echo [0;36;44m  บ              [0;37;44mA T O M I C   G A M E S   /   SCENARIO COMMAND              [0;36;44mบ
echo [0;36;44m  ฬออออออออออออออออออออออออออออออออออออออออออออออออออออออออออออออออออออออออออน
echo [0;36;44m  บ[1;36m  D-DAY  /  AMERICA INVADES!                                              [0;36;44mบ
echo [0;36;44m  บ[0;37;44m  NORMANDY, FRANCE  //  1944                                              [0;36;44mบ
echo [0;36;44m  บ                                                                          [0;36;44mบ
echo [0;36;44m  บ[0;37;44m  KEY   SCENARIO   OPERATION                                              [0;36;44mบ
echo [0;36;44m  วฤฤฤฤฤฤฤฤฤฤฤฤฤฤฤฤฤฤฤฤฤฤฤฤฤฤฤฤฤฤฤฤฤฤฤฤฤฤฤฤฤฤฤฤฤฤฤฤฤฤฤฤฤฤฤฤฤฤฤฤฤฤฤฤฤฤฤฤฤฤฤฤฤฤถ
echo [0;36;44m  บ[1;33m  [1]   [1;36mBRADLEY   [1;37mBradley's Nightmare                                     [0;36;44mบ
echo [0;36;44m  บ[1;33m  [2]   [1;36mCOUNTER   [1;37mSS Counterattack                                        [0;36;44mบ
echo [0;36;44m  บ[1;33m  [3]   [1;36mSTLO      [1;37mSt Lo                                                   [0;36;44mบ
echo [0;36;44m  บ[1;33m  [4]   [1;36mCOBRA     [1;37mOperation Cobra                                         [0;36;44mบ
echo [0;36;44m  บ[1;33m  [5]   [1;36mUTAH      [1;37mUtah Beach                                              [0;36;44mบ
echo [0;36;44m  บ[1;33m  [6]   [1;36mOMAHA     [1;37mOmaha Beach                                             [0;36;44mบ
echo [0;36;44m  บ[1;33m  [7]   [1;36mCAMPAIGN  [1;37mAmerica Invades!                                        [0;36;44mบ
echo [0;36;44m  บ                                                                          [0;36;44mบ
echo [0;36;44m  บ                                                                          [0;36;44mบ
echo [0;36;44m  บ                                                                          [0;36;44mบ
echo [0;36;44m  บ                                                                          [0;36;44mบ
echo [0;36;44m  บ[1;33m  [0]   [1;37mBack[0;37;44m                  Press the highlighted key                   [0;36;44mบ
echo [0;36;44m  ศออออออออออออออออออออออออออออออออออออออออออออออออออออออออออออออออออออออออออผ
choice /c:12345670 /n "[1;33;44m    Select operation: [1;37m"
if errorlevel 255 goto nochoice
if errorlevel 8 goto main
if errorlevel 7 goto dd07
if errorlevel 6 goto dd06
if errorlevel 5 goto dd05
if errorlevel 4 goto dd04
if errorlevel 3 goto dd03
if errorlevel 2 goto dd02
if errorlevel 1 goto dd01
goto nochoice

:ddargs
if "%2"=="BRADLEY" goto dd01
if "%2"=="COUNTER" goto dd02
if "%2"=="STLO" goto dd03
if "%2"=="COBRA" goto dd04
if "%2"=="UTAH" goto dd05
if "%2"=="OMAHA" goto dd06
if "%2"=="CAMPAIGN" goto dd07
goto usage

:dd01
set WAWDST=BRADLEY
echo [0m[2J[H
echo [1;33m  Selected: Bradley's Nightmare[0m
goto native

:dd02
set WAWDST=COUNTER
echo [0m[2J[H
echo [1;33m  Selected: SS Counterattack[0m
goto native

:dd03
set WAWDST=STLO
echo [0m[2J[H
echo [1;33m  Selected: St Lo[0m
goto native

:dd04
set WAWDST=COBRA
echo [0m[2J[H
echo [1;33m  Selected: Operation Cobra[0m
goto native

:dd05
set WAWDST=UTAH
echo [0m[2J[H
echo [1;33m  Selected: Utah Beach[0m
goto native

:dd06
set WAWDST=OMAHA
echo [0m[2J[H
echo [1;33m  Selected: Omaha Beach[0m
goto native

:dd07
set WAWDST=CAMPAIGN
echo [0m[2J[H
echo [1;33m  Selected: America Invades![0m
goto native

:native
if not exist SCENARIO\%WAWDST%.SCN goto nodday
echo [1;32mNative scenario ready: SCENARIO\%WAWDST%.SCN[0m
echo No staging is needed.
goto ready

:nodday
echo [1;31mMissing native D-Day scenario: SCENARIO\%WAWDST%.SCN[0m
echo Restore it from your original D-Day installation.
goto failed

:v4menu
echo [0;37;44m
cls
echo.
echo [0;36;44m  ษออออออออออออออออออออออออออออออออออออออออออออออออออออออออออออออออออออออออออป
echo [0;36;44m  บ                     [1;33mฑฑ  [1;37mW O R L D   A T   W A R[1;33m  ฑฑ                      [0;36;44mบ
echo [0;36;44m  บ              [0;37;44mA T O M I C   G A M E S   /   SCENARIO COMMAND              [0;36;44mบ
echo [0;36;44m  ฬออออออออออออออออออออออออออออออออออออออออออออออออออออออออออออออออออออออออออน
echo [0;36;44m  บ[1;32m  V FOR VICTORY                                                           [0;36;44mบ
echo [0;36;44m  บ[0;37;44m  Select a battleset from the original series.                            [0;36;44mบ
echo [0;36;44m  บ                                                                          [0;36;44mบ
echo [0;36;44m  บ[0;37;44m  KEY   CAMPAIGN / THEATER                                                [0;36;44mบ
echo [0;36;44m  วฤฤฤฤฤฤฤฤฤฤฤฤฤฤฤฤฤฤฤฤฤฤฤฤฤฤฤฤฤฤฤฤฤฤฤฤฤฤฤฤฤฤฤฤฤฤฤฤฤฤฤฤฤฤฤฤฤฤฤฤฤฤฤฤฤฤฤฤฤฤฤฤฤฤถ
echo [0;36;44m  บ[1;33m  [1]   [1;32mGOLD / JUNO / SWORD         [0;37;44mNormandy                              [0;36;44mบ
echo [0;36;44m  บ                                                                          [0;36;44mบ
echo [0;36;44m  บ[1;33m  [2]   [1;32mMARKET GARDEN               [0;37;44mThe Netherlands                       [0;36;44mบ
echo [0;36;44m  บ                                                                          [0;36;44mบ
echo [0;36;44m  บ[1;33m  [3]   [1;32mUTAH BEACH                  [0;37;44mNormandy                              [0;36;44mบ
echo [0;36;44m  บ                                                                          [0;36;44mบ
echo [0;36;44m  บ[1;33m  [4]   [1;32mVELIKIYE LUKI               [0;37;44mEastern Front                         [0;36;44mบ
echo [0;36;44m  บ                                                                          [0;36;44mบ
echo [0;36;44m  บ                                                                          [0;36;44mบ
echo [0;36;44m  บ                                                                          [0;36;44mบ
echo [0;36;44m  บ                                                                          [0;36;44mบ
echo [0;36;44m  บ[1;33m  [0]   [1;37mBack[0;37;44m                  Press the highlighted key                   [0;36;44mบ
echo [0;36;44m  ศออออออออออออออออออออออออออออออออออออออออออออออออออออออออออออออออออออออออออผ
choice /c:12340 /n "[1;33;44m    Select battleset: [1;37m"
if errorlevel 255 goto nochoice
if errorlevel 5 goto main
if errorlevel 4 goto vlmenu
if errorlevel 3 goto ubmenu
if errorlevel 2 goto mgmenu
if errorlevel 1 goto gjsmenu
goto nochoice

:stmenu
echo [0;37;44m
cls
echo.
echo [0;36;44m  ษออออออออออออออออออออออออออออออออออออออออออออออออออออออออออออออออออออออออออป
echo [0;36;44m  บ                     [1;33mฑฑ  [1;37mW O R L D   A T   W A R[1;33m  ฑฑ                      [0;36;44mบ
echo [0;36;44m  บ              [0;37;44mA T O M I C   G A M E S   /   SCENARIO COMMAND              [0;36;44mบ
echo [0;36;44m  ฬออออออออออออออออออออออออออออออออออออออออออออออออออออออออออออออออออออออออออน
echo [0;36;44m  บ[1;31m  STALINGRAD                                                              [0;36;44mบ
echo [0;36;44m  บ[0;37;44m  EASTERN FRONT  //  1942 - 1943                                          [0;36;44mบ
echo [0;36;44m  บ                                                                          [0;36;44mบ
echo [0;36;44m  บ[0;37;44m  KEY   SCENARIO   OPERATION                                              [0;36;44mบ
echo [0;36;44m  วฤฤฤฤฤฤฤฤฤฤฤฤฤฤฤฤฤฤฤฤฤฤฤฤฤฤฤฤฤฤฤฤฤฤฤฤฤฤฤฤฤฤฤฤฤฤฤฤฤฤฤฤฤฤฤฤฤฤฤฤฤฤฤฤฤฤฤฤฤฤฤฤฤฤถ
echo [0;36;44m  บ[1;33m  [1]   [1;36mCAMPAIGN  [1;37mOperation Uranus                                        [0;36;44mบ
echo [0;36;44m  บ[1;33m  [2]   [1;36mCITY      [1;37mRattenkrieg                                             [0;36;44mบ
echo [0;36;44m  บ[1;33m  [3]   [1;36mCLASH     [1;37mA River Too Far                                         [0;36;44mบ
echo [0;36;44m  บ[1;33m  [4]   [1;36mHURBERT   [1;37mTo the Volga!                                           [0;36;44mบ
echo [0;36;44m  บ[1;33m  [5]   [1;36mMANSTEIN  [1;37mManstein's Solution                                     [0;36;44mบ
echo [0;36;44m  บ[1;33m  [6]   [1;36mQUIET     [1;37mQuiet Flows the Don                                     [0;36;44mบ
echo [0;36;44m  บ[1;33m  [7]   [1;36mRIVER     [1;37mA River Too Far                                         [0;36;44mบ
echo [0;36;44m  บ[1;33m  [8]   [1;36mTANKS     [1;37mManstein's Solution                                     [0;36;44mบ
echo [0;36;44m  บ[1;33m  [9]   [1;36mVOLGA     [1;37mTo the Volga!                                           [0;36;44mบ
echo [0;36;44m  บ[1;33m  [A]   [1;36mWINTER    [1;37mWintergewitter                                          [0;36;44mบ
echo [0;36;44m  บ                                                                          [0;36;44mบ
echo [0;36;44m  บ[1;33m  [0]   [1;37mBack[0;37;44m                  Press the highlighted key                   [0;36;44mบ
echo [0;36;44m  ศออออออออออออออออออออออออออออออออออออออออออออออออออออออออออออออออออออออออออผ
choice /c:123456789A0 /n "[1;33;44m    Select operation: [1;37m"
if errorlevel 255 goto nochoice
if errorlevel 11 goto main
if errorlevel 10 goto pick10
if errorlevel 9 goto pick09
if errorlevel 8 goto pick08
if errorlevel 7 goto pick07
if errorlevel 6 goto pick06
if errorlevel 5 goto pick05
if errorlevel 4 goto pick04
if errorlevel 3 goto pick03
if errorlevel 2 goto pick02
if errorlevel 1 goto pick01
goto nochoice

:ocmenu
echo [0;37;44m
cls
echo.
echo [0;36;44m  ษออออออออออออออออออออออออออออออออออออออออออออออออออออออออออออออออออออออออออป
echo [0;36;44m  บ                     [1;33mฑฑ  [1;37mW O R L D   A T   W A R[1;33m  ฑฑ                      [0;36;44mบ
echo [0;36;44m  บ              [0;37;44mA T O M I C   G A M E S   /   SCENARIO COMMAND              [0;36;44mบ
echo [0;36;44m  ฬออออออออออออออออออออออออออออออออออออออออออออออออออออออออออออออออออออออออออน
echo [0;36;44m  บ[1;33m  OPERATION CRUSADER                                                      [0;36;44mบ
echo [0;36;44m  บ[0;37;44m  NORTH AFRICA  //  1941                                                  [0;36;44mบ
echo [0;36;44m  บ                                                                          [0;36;44mบ
echo [0;36;44m  บ[0;37;44m  KEY   SCENARIO   OPERATION                                              [0;36;44mบ
echo [0;36;44m  วฤฤฤฤฤฤฤฤฤฤฤฤฤฤฤฤฤฤฤฤฤฤฤฤฤฤฤฤฤฤฤฤฤฤฤฤฤฤฤฤฤฤฤฤฤฤฤฤฤฤฤฤฤฤฤฤฤฤฤฤฤฤฤฤฤฤฤฤฤฤฤฤฤฤถ
echo [0;36;44m  บ[1;33m  [1]   [1;36mCAMPAIGN  [1;37mOperation Crusader                                      [0;36;44mบ
echo [0;36;44m  บ[1;33m  [2]   [1;36mDUCE      [1;37mIl Duce's Finest                                        [0;36;44mบ
echo [0;36;44m  บ[1;33m  [3]   [1;36mHELLFIRE  [1;37mHell Fire Pass                                          [0;36;44mบ
echo [0;36;44m  บ[1;33m  [4]   [1;36mRELIEVED  [1;37mTobruk Relieved                                         [0;36;44mบ
echo [0;36;44m  บ[1;33m  [5]   [1;36mRESCUE    [1;37mTo The Rescue!                                          [0;36;44mบ
echo [0;36;44m  บ[1;33m  [6]   [1;36mTOBRUK    [1;37mFortress Tobruk                                         [0;36;44mบ
echo [0;36;44m  บ                                                                          [0;36;44mบ
echo [0;36;44m  บ                                                                          [0;36;44mบ
echo [0;36;44m  บ                                                                          [0;36;44mบ
echo [0;36;44m  บ                                                                          [0;36;44mบ
echo [0;36;44m  บ                                                                          [0;36;44mบ
echo [0;36;44m  บ[1;33m  [0]   [1;37mBack[0;37;44m                  Press the highlighted key                   [0;36;44mบ
echo [0;36;44m  ศออออออออออออออออออออออออออออออออออออออออออออออออออออออออออออออออออออออออออผ
choice /c:1234560 /n "[1;33;44m    Select operation: [1;37m"
if errorlevel 255 goto nochoice
if errorlevel 7 goto main
if errorlevel 6 goto pick16
if errorlevel 5 goto pick15
if errorlevel 4 goto pick14
if errorlevel 3 goto pick13
if errorlevel 2 goto pick12
if errorlevel 1 goto pick11
goto nochoice

:gjsmenu
echo [0;37;44m
cls
echo.
echo [0;36;44m  ษออออออออออออออออออออออออออออออออออออออออออออออออออออออออออออออออออออออออออป
echo [0;36;44m  บ                     [1;33mฑฑ  [1;37mW O R L D   A T   W A R[1;33m  ฑฑ                      [0;36;44mบ
echo [0;36;44m  บ              [0;37;44mA T O M I C   G A M E S   /   SCENARIO COMMAND              [0;36;44mบ
echo [0;36;44m  ฬออออออออออออออออออออออออออออออออออออออออออออออออออออออออออออออออออออออออออน
echo [0;36;44m  บ[1;32m  GOLD / JUNO / SWORD                                                     [0;36;44mบ
echo [0;36;44m  บ[0;37;44m  NORMANDY, FRANCE  //  1944                                              [0;36;44mบ
echo [0;36;44m  บ                                                                          [0;36;44mบ
echo [0;36;44m  บ[0;37;44m  KEY   SCENARIO   OPERATION                                              [0;36;44mบ
echo [0;36;44m  วฤฤฤฤฤฤฤฤฤฤฤฤฤฤฤฤฤฤฤฤฤฤฤฤฤฤฤฤฤฤฤฤฤฤฤฤฤฤฤฤฤฤฤฤฤฤฤฤฤฤฤฤฤฤฤฤฤฤฤฤฤฤฤฤฤฤฤฤฤฤฤฤฤฤถ
echo [0;36;44m  บ[1;33m  [1]   [1;36mGJSBEACH  [1;37mOff the Beaches                                         [0;36;44mบ
echo [0;36;44m  บ[1;33m  [2]   [1;36mGJSBULL   [1;37mCharge of the Bull                                      [0;36;44mบ
echo [0;36;44m  บ[1;33m  [3]   [1;36mGJSCAMP   [1;37mTo Caen!                                                [0;36;44mบ
echo [0;36;44m  บ[1;33m  [4]   [1;36mGJSORNE   [1;37mThe Orne Bridges                                        [0;36;44mบ
echo [0;36;44m  บ[1;33m  [5]   [1;36mGJSRUN    [1;37mThe End Run                                             [0;36;44mบ
echo [0;36;44m  บ[1;33m  [6]   [1;36mGJSSEA    [1;37mTo the Sea                                              [0;36;44mบ
echo [0;36;44m  บ[1;33m  [7]   [1;36mGJSYOUTH  [1;37mAttack of the 12th SS                                   [0;36;44mบ
echo [0;36;44m  บ                                                                          [0;36;44mบ
echo [0;36;44m  บ                                                                          [0;36;44mบ
echo [0;36;44m  บ                                                                          [0;36;44mบ
echo [0;36;44m  บ                                                                          [0;36;44mบ
echo [0;36;44m  บ[1;33m  [0]   [1;37mBack[0;37;44m                  Press the highlighted key                   [0;36;44mบ
echo [0;36;44m  ศออออออออออออออออออออออออออออออออออออออออออออออออออออออออออออออออออออออออออผ
choice /c:12345670 /n "[1;33;44m    Select operation: [1;37m"
if errorlevel 255 goto nochoice
if errorlevel 8 goto v4menu
if errorlevel 7 goto pick23
if errorlevel 6 goto pick22
if errorlevel 5 goto pick21
if errorlevel 4 goto pick20
if errorlevel 3 goto pick19
if errorlevel 2 goto pick18
if errorlevel 1 goto pick17
goto nochoice

:mgmenu
echo [0;37;44m
cls
echo.
echo [0;36;44m  ษออออออออออออออออออออออออออออออออออออออออออออออออออออออออออออออออออออออออออป
echo [0;36;44m  บ                     [1;33mฑฑ  [1;37mW O R L D   A T   W A R[1;33m  ฑฑ                      [0;36;44mบ
echo [0;36;44m  บ              [0;37;44mA T O M I C   G A M E S   /   SCENARIO COMMAND              [0;36;44mบ
echo [0;36;44m  ฬออออออออออออออออออออออออออออออออออออออออออออออออออออออออออออออออออออออออออน
echo [0;36;44m  บ[1;32m  MARKET GARDEN                                                           [0;36;44mบ
echo [0;36;44m  บ[0;37;44m  THE NETHERLANDS  //  1944                                               [0;36;44mบ
echo [0;36;44m  บ                                                                          [0;36;44mบ
echo [0;36;44m  บ[0;37;44m  KEY   SCENARIO   OPERATION                                              [0;36;44mบ
echo [0;36;44m  วฤฤฤฤฤฤฤฤฤฤฤฤฤฤฤฤฤฤฤฤฤฤฤฤฤฤฤฤฤฤฤฤฤฤฤฤฤฤฤฤฤฤฤฤฤฤฤฤฤฤฤฤฤฤฤฤฤฤฤฤฤฤฤฤฤฤฤฤฤฤฤฤฤฤถ
echo [0;36;44m  บ[1;33m  [1]   [1;36mMGBREAK   [1;37mBreakout of 30th Corps                                  [0;36;44mบ
echo [0;36;44m  บ[1;33m  [2]   [1;36mMGCAMP    [1;37m"A Bridge Too Far"                                      [0;36;44mบ
echo [0;36;44m  บ[1;33m  [3]   [1;36mMGDEST    [1;37mDestruction of the 1st                                  [0;36;44mบ
echo [0;36;44m  บ[1;33m  [4]   [1;36mMGEAGLES  [1;37mScreaming Eagles                                        [0;36;44mบ
echo [0;36;44m  บ[1;33m  [5]   [1;36mMGFIRST   [1;37mThe First Bridge                                        [0;36;44mบ
echo [0;36;44m  บ[1;33m  [6]   [1;36mMGHEIGHT  [1;37mGroesbeeck Heights                                      [0;36;44mบ
echo [0;36;44m  บ[1;33m  [7]   [1;36mMGHELL    [1;37mHell's Highway                                          [0;36;44mบ
echo [0;36;44m  บ                                                                          [0;36;44mบ
echo [0;36;44m  บ                                                                          [0;36;44mบ
echo [0;36;44m  บ                                                                          [0;36;44mบ
echo [0;36;44m  บ                                                                          [0;36;44mบ
echo [0;36;44m  บ[1;33m  [0]   [1;37mBack[0;37;44m                  Press the highlighted key                   [0;36;44mบ
echo [0;36;44m  ศออออออออออออออออออออออออออออออออออออออออออออออออออออออออออออออออออออออออออผ
choice /c:12345670 /n "[1;33;44m    Select operation: [1;37m"
if errorlevel 255 goto nochoice
if errorlevel 8 goto v4menu
if errorlevel 7 goto pick30
if errorlevel 6 goto pick29
if errorlevel 5 goto pick28
if errorlevel 4 goto pick27
if errorlevel 3 goto pick26
if errorlevel 2 goto pick25
if errorlevel 1 goto pick24
goto nochoice

:ubmenu
echo [0;37;44m
cls
echo.
echo [0;36;44m  ษออออออออออออออออออออออออออออออออออออออออออออออออออออออออออออออออออออออออออป
echo [0;36;44m  บ                     [1;33mฑฑ  [1;37mW O R L D   A T   W A R[1;33m  ฑฑ                      [0;36;44mบ
echo [0;36;44m  บ              [0;37;44mA T O M I C   G A M E S   /   SCENARIO COMMAND              [0;36;44mบ
echo [0;36;44m  ฬออออออออออออออออออออออออออออออออออออออออออออออออออออออออออออออออออออออออออน
echo [0;36;44m  บ[1;32m  UTAH BEACH                                                              [0;36;44mบ
echo [0;36;44m  บ[0;37;44m  NORMANDY, FRANCE  //  1944                                              [0;36;44mบ
echo [0;36;44m  บ                                                                          [0;36;44mบ
echo [0;36;44m  บ[0;37;44m  KEY   SCENARIO   OPERATION                                              [0;36;44mบ
echo [0;36;44m  วฤฤฤฤฤฤฤฤฤฤฤฤฤฤฤฤฤฤฤฤฤฤฤฤฤฤฤฤฤฤฤฤฤฤฤฤฤฤฤฤฤฤฤฤฤฤฤฤฤฤฤฤฤฤฤฤฤฤฤฤฤฤฤฤฤฤฤฤฤฤฤฤฤฤถ
echo [0;36;44m  บ[1;33m  [1]   [1;36mUBATTACK  [1;37mSS Counter Attack                                       [0;36;44mบ
echo [0;36;44m  บ[1;33m  [2]   [1;36mUBCAMP    [1;37mCampaign                                                [0;36;44mบ
echo [0;36;44m  บ[1;33m  [3]   [1;36mUBCARENT  [1;37mObjective Carentan                                      [0;36;44mบ
echo [0;36;44m  บ[1;33m  [4]   [1;36mUBCARTER  [1;37mRace for Carteret                                       [0;36;44mบ
echo [0;36;44m  บ[1;33m  [5]   [1;36mUBFINAL   [1;37mFinal Assault                                           [0;36;44mบ
echo [0;36;44m  บ[1;33m  [6]   [1;36mUBMOP     [1;37mMopping Up                                              [0;36;44mบ
echo [0;36;44m  บ                                                                          [0;36;44mบ
echo [0;36;44m  บ                                                                          [0;36;44mบ
echo [0;36;44m  บ                                                                          [0;36;44mบ
echo [0;36;44m  บ                                                                          [0;36;44mบ
echo [0;36;44m  บ                                                                          [0;36;44mบ
echo [0;36;44m  บ[1;33m  [0]   [1;37mBack[0;37;44m                  Press the highlighted key                   [0;36;44mบ
echo [0;36;44m  ศออออออออออออออออออออออออออออออออออออออออออออออออออออออออออออออออออออออออออผ
choice /c:1234560 /n "[1;33;44m    Select operation: [1;37m"
if errorlevel 255 goto nochoice
if errorlevel 7 goto v4menu
if errorlevel 6 goto pick36
if errorlevel 5 goto pick35
if errorlevel 4 goto pick34
if errorlevel 3 goto pick33
if errorlevel 2 goto pick32
if errorlevel 1 goto pick31
goto nochoice

:vlmenu
echo [0;37;44m
cls
echo.
echo [0;36;44m  ษออออออออออออออออออออออออออออออออออออออออออออออออออออออออออออออออออออออออออป
echo [0;36;44m  บ                     [1;33mฑฑ  [1;37mW O R L D   A T   W A R[1;33m  ฑฑ                      [0;36;44mบ
echo [0;36;44m  บ              [0;37;44mA T O M I C   G A M E S   /   SCENARIO COMMAND              [0;36;44mบ
echo [0;36;44m  ฬออออออออออออออออออออออออออออออออออออออออออออออออออออออออออออออออออออออออออน
echo [0;36;44m  บ[1;32m  VELIKIYE LUKI                                                           [0;36;44mบ
echo [0;36;44m  บ[0;37;44m  EASTERN FRONT  //  1942 - 1943                                          [0;36;44mบ
echo [0;36;44m  บ                                                                          [0;36;44mบ
echo [0;36;44m  บ[0;37;44m  KEY   SCENARIO   OPERATION                                              [0;36;44mบ
echo [0;36;44m  วฤฤฤฤฤฤฤฤฤฤฤฤฤฤฤฤฤฤฤฤฤฤฤฤฤฤฤฤฤฤฤฤฤฤฤฤฤฤฤฤฤฤฤฤฤฤฤฤฤฤฤฤฤฤฤฤฤฤฤฤฤฤฤฤฤฤฤฤฤฤฤฤฤฤถ
echo [0;36;44m  บ[1;33m  [1]   [1;36mVLCAMP    [1;37mCampaign                                                [0;36;44mบ
echo [0;36;44m  บ[1;33m  [2]   [1;36mVLCITY    [1;37mInto the City                                           [0;36;44mบ
echo [0;36;44m  บ[1;33m  [3]   [1;36mVLEIGHT   [1;37mEight More Kilometers                                   [0;36;44mบ
echo [0;36;44m  บ[1;33m  [4]   [1;36mVLFORT    [1;37mFortress in the Snow                                    [0;36;44mบ
echo [0;36;44m  บ[1;33m  [5]   [1;36mVLLAST    [1;37mLast Chance                                             [0;36;44mบ
echo [0;36;44m  บ[1;33m  [6]   [1;36mVLRESCUE  [1;37mTo the Rescue                                           [0;36;44mบ
echo [0;36;44m  บ[1;33m  [7]   [1;36mVLSTORM   [1;37mRed Storm                                               [0;36;44mบ
echo [0;36;44m  บ                                                                          [0;36;44mบ
echo [0;36;44m  บ                                                                          [0;36;44mบ
echo [0;36;44m  บ                                                                          [0;36;44mบ
echo [0;36;44m  บ                                                                          [0;36;44mบ
echo [0;36;44m  บ[1;33m  [0]   [1;37mBack[0;37;44m                  Press the highlighted key                   [0;36;44mบ
echo [0;36;44m  ศออออออออออออออออออออออออออออออออออออออออออออออออออออออออออออออออออออออออออผ
choice /c:12345670 /n "[1;33;44m    Select operation: [1;37m"
if errorlevel 255 goto nochoice
if errorlevel 8 goto v4menu
if errorlevel 7 goto pick43
if errorlevel 6 goto pick42
if errorlevel 5 goto pick41
if errorlevel 4 goto pick40
if errorlevel 3 goto pick39
if errorlevel 2 goto pick38
if errorlevel 1 goto pick37
goto nochoice

:stargs
if "%2"=="CAMPAIGN" goto pick01
if "%2"=="CITY" goto pick02
if "%2"=="CLASH" goto pick03
if "%2"=="HURBERT" goto pick04
if "%2"=="MANSTEIN" goto pick05
if "%2"=="QUIET" goto pick06
if "%2"=="RIVER" goto pick07
if "%2"=="TANKS" goto pick08
if "%2"=="VOLGA" goto pick09
if "%2"=="WINTER" goto pick10
goto usage

:ocargs
if "%2"=="CAMPAIGN" goto pick11
if "%2"=="DUCE" goto pick12
if "%2"=="HELLFIRE" goto pick13
if "%2"=="RELIEVED" goto pick14
if "%2"=="RESCUE" goto pick15
if "%2"=="TOBRUK" goto pick16
goto usage

:v4args
if "%2"=="GJSBEACH" goto pick17
if "%2"=="GJSBULL" goto pick18
if "%2"=="GJSCAMP" goto pick19
if "%2"=="GJSORNE" goto pick20
if "%2"=="GJSRUN" goto pick21
if "%2"=="GJSSEA" goto pick22
if "%2"=="GJSYOUTH" goto pick23
if "%2"=="MGBREAK" goto pick24
if "%2"=="MGCAMP" goto pick25
if "%2"=="MGDEST" goto pick26
if "%2"=="MGEAGLES" goto pick27
if "%2"=="MGFIRST" goto pick28
if "%2"=="MGHEIGHT" goto pick29
if "%2"=="MGHELL" goto pick30
if "%2"=="UBATTACK" goto pick31
if "%2"=="UBCAMP" goto pick32
if "%2"=="UBCARENT" goto pick33
if "%2"=="UBCARTER" goto pick34
if "%2"=="UBFINAL" goto pick35
if "%2"=="UBMOP" goto pick36
if "%2"=="VLCAMP" goto pick37
if "%2"=="VLCITY" goto pick38
if "%2"=="VLEIGHT" goto pick39
if "%2"=="VLFORT" goto pick40
if "%2"=="VLLAST" goto pick41
if "%2"=="VLRESCUE" goto pick42
if "%2"=="VLSTORM" goto pick43
goto usage

:pick01
set WAWDIR=STALINGR
set WAWSRC=CAMPAIGN
set WAWDST=STCAMP
echo [0m[2J[H
echo [1;33m  Selected: Operation Uranus[0m
goto stage

:pick02
set WAWDIR=STALINGR
set WAWSRC=CITY
set WAWDST=STCITY
echo [0m[2J[H
echo [1;33m  Selected: Rattenkrieg[0m
goto stage

:pick03
set WAWDIR=STALINGR
set WAWSRC=CLASH
set WAWDST=STCLASH
echo [0m[2J[H
echo [1;33m  Selected: A River Too Far[0m
goto stage

:pick04
set WAWDIR=STALINGR
set WAWSRC=HURBERT
set WAWDST=STHURBER
echo [0m[2J[H
echo [1;33m  Selected: To the Volga![0m
goto stage

:pick05
set WAWDIR=STALINGR
set WAWSRC=MANSTEIN
set WAWDST=STMANSTE
echo [0m[2J[H
echo [1;33m  Selected: Manstein's Solution[0m
goto stage

:pick06
set WAWDIR=STALINGR
set WAWSRC=QUIET
set WAWDST=STQUIET
echo [0m[2J[H
echo [1;33m  Selected: Quiet Flows the Don[0m
goto stage

:pick07
set WAWDIR=STALINGR
set WAWSRC=RIVER
set WAWDST=STRIVER
echo [0m[2J[H
echo [1;33m  Selected: A River Too Far[0m
goto stage

:pick08
set WAWDIR=STALINGR
set WAWSRC=TANKS
set WAWDST=STTANKS
echo [0m[2J[H
echo [1;33m  Selected: Manstein's Solution[0m
goto stage

:pick09
set WAWDIR=STALINGR
set WAWSRC=VOLGA
set WAWDST=STVOLGA
echo [0m[2J[H
echo [1;33m  Selected: To the Volga![0m
goto stage

:pick10
set WAWDIR=STALINGR
set WAWSRC=WINTER
set WAWDST=STWINTER
echo [0m[2J[H
echo [1;33m  Selected: Wintergewitter[0m
goto stage

:pick11
set WAWDIR=CRUSADER
set WAWSRC=CAMPAIGN
set WAWDST=OCCAMP
echo [0m[2J[H
echo [1;33m  Selected: Operation Crusader[0m
goto stage

:pick12
set WAWDIR=CRUSADER
set WAWSRC=DUCE
set WAWDST=OCDUCE
echo [0m[2J[H
echo [1;33m  Selected: Il Duce's Finest[0m
goto stage

:pick13
set WAWDIR=CRUSADER
set WAWSRC=HELLFIRE
set WAWDST=OCHELLFI
echo [0m[2J[H
echo [1;33m  Selected: Hell Fire Pass[0m
goto stage

:pick14
set WAWDIR=CRUSADER
set WAWSRC=RELIEVED
set WAWDST=OCRELIEV
echo [0m[2J[H
echo [1;33m  Selected: Tobruk Relieved[0m
goto stage

:pick15
set WAWDIR=CRUSADER
set WAWSRC=RESCUE
set WAWDST=OCRESCUE
echo [0m[2J[H
echo [1;33m  Selected: To The Rescue![0m
goto stage

:pick16
set WAWDIR=CRUSADER
set WAWSRC=TOBRUK
set WAWDST=OCTOBRUK
echo [0m[2J[H
echo [1;33m  Selected: Fortress Tobruk[0m
goto stage

:pick17
set WAWDIR=V4V
set WAWSRC=GJSBEACH
set WAWDST=GJSBEACH
echo [0m[2J[H
echo [1;33m  Selected: Off the Beaches[0m
goto stage

:pick18
set WAWDIR=V4V
set WAWSRC=GJSBULL
set WAWDST=GJSBULL
echo [0m[2J[H
echo [1;33m  Selected: Charge of the Bull[0m
goto stage

:pick19
set WAWDIR=V4V
set WAWSRC=GJSCAMP
set WAWDST=GJSCAMP
echo [0m[2J[H
echo [1;33m  Selected: To Caen![0m
goto stage

:pick20
set WAWDIR=V4V
set WAWSRC=GJSORNE
set WAWDST=GJSORNE
echo [0m[2J[H
echo [1;33m  Selected: The Orne Bridges[0m
goto stage

:pick21
set WAWDIR=V4V
set WAWSRC=GJSRUN
set WAWDST=GJSRUN
echo [0m[2J[H
echo [1;33m  Selected: The End Run[0m
goto stage

:pick22
set WAWDIR=V4V
set WAWSRC=GJSSEA
set WAWDST=GJSSEA
echo [0m[2J[H
echo [1;33m  Selected: To the Sea[0m
goto stage

:pick23
set WAWDIR=V4V
set WAWSRC=GJSYOUTH
set WAWDST=GJSYOUTH
echo [0m[2J[H
echo [1;33m  Selected: Attack of the 12th SS[0m
goto stage

:pick24
set WAWDIR=V4V
set WAWSRC=MGBREAK
set WAWDST=MGBREAK
echo [0m[2J[H
echo [1;33m  Selected: Breakout of 30th Corps[0m
goto stage

:pick25
set WAWDIR=V4V
set WAWSRC=MGCAMP
set WAWDST=MGCAMP
echo [0m[2J[H
echo [1;33m  Selected: "A Bridge Too Far"[0m
goto stage

:pick26
set WAWDIR=V4V
set WAWSRC=MGDEST
set WAWDST=MGDEST
echo [0m[2J[H
echo [1;33m  Selected: Destruction of the 1st[0m
goto stage

:pick27
set WAWDIR=V4V
set WAWSRC=MGEAGLES
set WAWDST=MGEAGLES
echo [0m[2J[H
echo [1;33m  Selected: Screaming Eagles[0m
goto stage

:pick28
set WAWDIR=V4V
set WAWSRC=MGFIRST
set WAWDST=MGFIRST
echo [0m[2J[H
echo [1;33m  Selected: The First Bridge[0m
goto stage

:pick29
set WAWDIR=V4V
set WAWSRC=MGHEIGHT
set WAWDST=MGHEIGHT
echo [0m[2J[H
echo [1;33m  Selected: Groesbeeck Heights[0m
goto stage

:pick30
set WAWDIR=V4V
set WAWSRC=MGHELL
set WAWDST=MGHELL
echo [0m[2J[H
echo [1;33m  Selected: Hell's Highway[0m
goto stage

:pick31
set WAWDIR=V4V
set WAWSRC=UBATTACK
set WAWDST=UBATTACK
echo [0m[2J[H
echo [1;33m  Selected: SS Counter Attack[0m
goto stage

:pick32
set WAWDIR=V4V
set WAWSRC=UBCAMP
set WAWDST=UBCAMP
echo [0m[2J[H
echo [1;33m  Selected: Campaign[0m
goto stage

:pick33
set WAWDIR=V4V
set WAWSRC=UBCARENT
set WAWDST=UBCARENT
echo [0m[2J[H
echo [1;33m  Selected: Objective Carentan[0m
goto stage

:pick34
set WAWDIR=V4V
set WAWSRC=UBCARTER
set WAWDST=UBCARTER
echo [0m[2J[H
echo [1;33m  Selected: Race for Carteret[0m
goto stage

:pick35
set WAWDIR=V4V
set WAWSRC=UBFINAL
set WAWDST=UBFINAL
echo [0m[2J[H
echo [1;33m  Selected: Final Assault[0m
goto stage

:pick36
set WAWDIR=V4V
set WAWSRC=UBMOP
set WAWDST=UBMOP
echo [0m[2J[H
echo [1;33m  Selected: Mopping Up[0m
goto stage

:pick37
set WAWDIR=V4V
set WAWSRC=VLCAMP
set WAWDST=VLCAMP
echo [0m[2J[H
echo [1;33m  Selected: Campaign[0m
goto stage

:pick38
set WAWDIR=V4V
set WAWSRC=VLCITY
set WAWDST=VLCITY
echo [0m[2J[H
echo [1;33m  Selected: Into the City[0m
goto stage

:pick39
set WAWDIR=V4V
set WAWSRC=VLEIGHT
set WAWDST=VLEIGHT
echo [0m[2J[H
echo [1;33m  Selected: Eight More Kilometers[0m
goto stage

:pick40
set WAWDIR=V4V
set WAWSRC=VLFORT
set WAWDST=VLFORT
echo [0m[2J[H
echo [1;33m  Selected: Fortress in the Snow[0m
goto stage

:pick41
set WAWDIR=V4V
set WAWSRC=VLLAST
set WAWDST=VLLAST
echo [0m[2J[H
echo [1;33m  Selected: Last Chance[0m
goto stage

:pick42
set WAWDIR=V4V
set WAWSRC=VLRESCUE
set WAWDST=VLRESCUE
echo [0m[2J[H
echo [1;33m  Selected: To the Rescue[0m
goto stage

:pick43
set WAWDIR=V4V
set WAWSRC=VLSTORM
set WAWDST=VLSTORM
echo [0m[2J[H
echo [1;33m  Selected: Red Storm[0m
goto stage
:stage
if not exist SCENARIO\%WAWDIR%\%WAWSRC%.SCN goto missing
if not exist SCENARIO\%WAWDIR%\%WAWSRC%.REZ goto missing
if not exist SCENARIO\%WAWDIR%\%WAWSRC%.AI goto missing
rem Copy to temporary names first; never mistake an old file for a copy.
rem A child shell clears the status left by CHOICE on DOS COPY variants.
%COMSPEC% /c exit
if exist SCENARIO\%WAWDST%.$R del SCENARIO\%WAWDST%.$R
if exist SCENARIO\%WAWDST%.$R goto copyfail
if exist SCENARIO\%WAWDST%.$A del SCENARIO\%WAWDST%.$A
if exist SCENARIO\%WAWDST%.$A goto copyfail
if exist SCENARIO\%WAWDST%.$S del SCENARIO\%WAWDST%.$S
if exist SCENARIO\%WAWDST%.$S goto copyfail
echo [1;32mStaging %WAWDIR%\%WAWSRC% as %WAWDST%...[0m
copy /b /y /v SCENARIO\%WAWDIR%\%WAWSRC%.REZ SCENARIO\%WAWDST%.$R
if errorlevel 1 goto copyfail
if not exist SCENARIO\%WAWDST%.$R goto copyfail
copy /b /y /v SCENARIO\%WAWDIR%\%WAWSRC%.AI SCENARIO\%WAWDST%.$A
if errorlevel 1 goto copyfail
if not exist SCENARIO\%WAWDST%.$A goto copyfail
copy /b /y /v SCENARIO\%WAWDIR%\%WAWSRC%.SCN SCENARIO\%WAWDST%.$S
if errorlevel 1 goto copyfail
if not exist SCENARIO\%WAWDST%.$S goto copyfail
if exist SCENARIO\%WAWDST%.REZ del SCENARIO\%WAWDST%.REZ
if exist SCENARIO\%WAWDST%.REZ goto copyfail
ren SCENARIO\%WAWDST%.$R %WAWDST%.REZ
if exist SCENARIO\%WAWDST%.$R goto copyfail
if not exist SCENARIO\%WAWDST%.REZ goto copyfail
if exist SCENARIO\%WAWDST%.AI del SCENARIO\%WAWDST%.AI
if exist SCENARIO\%WAWDST%.AI goto copyfail
ren SCENARIO\%WAWDST%.$A %WAWDST%.AI
if exist SCENARIO\%WAWDST%.$A goto copyfail
if not exist SCENARIO\%WAWDST%.AI goto copyfail
if exist SCENARIO\%WAWDST%.SCN del SCENARIO\%WAWDST%.SCN
if exist SCENARIO\%WAWDST%.SCN goto copyfail
ren SCENARIO\%WAWDST%.$S %WAWDST%.SCN
if exist SCENARIO\%WAWDST%.$S goto copyfail
if not exist SCENARIO\%WAWDST%.SCN goto copyfail
echo.
echo [1;32mReady: SCENARIO\%WAWDST%.SCN with its matching REZ and AI.[0m
echo Other staged scenarios remain available, including for saved games.
goto ready

:ready
if not "%1"=="" goto done
rem Startup-selection patch reads this DOS basename before drawing the panel.
if exist WAWSTART.TXT del WAWSTART.TXT
if exist WAWSTART.TXT goto hintfail
echo %WAWDST%.SCN>WAWSTART.TXT
if not exist WAWSTART.TXT goto hintfail
echo [1;32mStarting INVADE with %WAWDST%.SCN selected...[0m
echo [0m
INVADE.EXE
if exist WAWSTART.TXT del WAWSTART.TXT
goto main

:hintfail
echo [1;31mCannot write WAWSTART.TXT. Check write access in the game directory.[0m
goto failed

:missing
echo.
echo [1;31mIncomplete DOS export: SCENARIO\%WAWDIR%\%WAWSRC%[0m
echo All three files must exist: .SCN, .REZ and .AI. Nothing was copied.
echo Use the prepared scenarios\dos pack; editor assets cannot be used in DOS.
goto failed

:copyfail
if exist SCENARIO\%WAWDST%.$R del SCENARIO\%WAWDST%.$R
if exist SCENARIO\%WAWDST%.$A del SCENARIO\%WAWDST%.$A
if exist SCENARIO\%WAWDST%.$S del SCENARIO\%WAWDST%.$S
echo.
echo [1;31mStaging failed. Check free space and write access, then run SELECT again.[0m
echo Do not start this scenario until all three files copy successfully.
goto failed

:failed
if not "%1"=="" goto done
pause
goto main

:noroot
echo [1;31mRun SELECT from your playing copy's game directory.[0m
echo It must contain patched INVADE.EXE, DATA\PCWATW.REZ and SCENARIO.
goto done

:nochoice
echo [1;31mCHOICE failed. Use MS-DOS 6.22 CHOICE.COM or DOSBox-X's built-in CHOICE.[0m
echo You can also stage directly without a menu:
goto usage

:usage
echo Usage: SELECT
echo    or: SELECT DDAY BRADLEY
echo    or: SELECT STALINGR CLASH
echo    or: SELECT CRUSADER CAMPAIGN
echo    or: SELECT V4V VLFORT
echo Use uppercase directory and scenario names, without .SCN.
echo With no arguments, the menu launches INVADE after each selection.
echo Arguments stage/check only, without CHOICE or launching the game.
goto done

:done
echo [0m
set WAWDIR=
set WAWSRC=
set WAWDST=
cls
