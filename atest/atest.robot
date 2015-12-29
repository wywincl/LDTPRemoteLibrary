*** Settings ***
Library    LDTPLibrary

*** Variables ***
${window}    frmCalculator

*** Test Cases ***
Test title
     Launch APP    gnome-calculator
    # 等待直到窗口${window}存在
    # 选择菜单标题栏    ${window}    mnuApplication;mnuPreferences
#    ${ret}=    等待直到窗口${window}中的对象${dialog}存在
#    打印日志    ${ret}
#    ${ret}=    Wait Till frmCalculator Exist
#    Log    ${ret}

*** Keywords ***
