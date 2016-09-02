*** Settings ***

Library         BuiltIn
Library         Selenium2Library  timeout=5  implicit_wait=0.2
Library         String
Resource        keywords.txt
Library         bika.lims.testing.Keywords
Resource        plone/app/robotframework/selenium.robot
Library         Remote  ${PLONEURL}/RobotRemote
Variables       plone/app/testing/interfaces.py
Variables       bika/lims/tests/variables.py

Suite Setup     Start browser
Suite Teardown  Close All Browsers

Library         DebugLibrary

*** Variables ***
${input_identifier} =  lachat_quickchem_fia
${ASId} =  K04
${ASCategory} =  Water Chemistry
${ASTitle} =  K04
${ClientSampleId} =  A00035640001
${InstrumentName} =  Lachat QuickChem FIA
${InstrumentFile} =  QuickChemFIA.csv
${InstrumentFileFormat} =  CSV

*** Test Cases ***

Lachat QuickChem FIA
    [Documentation]  First we have to create the AS to match the
    ...              analysis in the file. Then we have to create the AR
    ...              and tranistion it. Finally qe can import the results.
    Enable autologin as  LabManager
    set autologin username  test_labmanager
    ${PATH_TO_TEST} =  run keyword  resource_filename
    Disable stickers
    Create Analysis Service  ${ASId}  ${ASTitle}

    Import Instrument File     ${InstrumentName}  ${PATH_TO_TEST}/files/${InstrumentFile}  ${input_identifier}
    page should not contain    Service keyword ${ASId} not found

*** Keywords ***

Start browser
    Open browser                        ${PLONEURL}/login_form  chrome
    Log in                              test_labmanager         test_labmanager
    Wait until page contains            You are now logged in
    Set selenium speed                  ${SELENIUM_SPEED}

Create Analysis Service
   [Documentation]  Create an AS using the ID ASId
   [Arguments]  ${ASId}
   ...          ${ASTitle1}
   Go to                       ${PLONEURL}/bika_setup/bika_analysisservices
   Wait until page contains element    css=h1
   Click link                  link=Add
   Wait until page contains element  title
   Input text                  title  ${ASTitle1}
   Input text                  ShortTitle  ${ASId}
   Input text                  Keyword  ${ASId}
   Select from dropdown        Category  ${ASCategory}
   Click button                Save
   Wait until page contains    Changes saved.

Import Instrument File
    [Documentation]  Select the instrument and file type.
    ...              Then import the file created by the instrument.
    [arguments]  ${instrument}  ${file}  ${input_identifier}
    Go to                       ${PLONEURL}
    Click Link                  Import
    Wait until page contains    Select a data interface
    Select from list            exim  ${instrument}
    Element Should Contain      ${input_identifier}_format  ${InstrumentFileFormat}
    Import AR Results Instrument File    ${file}  ${input_identifier}_file

Import AR Results Instrument File
    [Documentation]  Import the file from test files folder, and submit it.
    [arguments]                 ${file}
    ...                         ${input_identifier}
    Choose File                 ${input_identifier}  ${file}
    Click Button                Submit
    Wait until page contains    Log trace