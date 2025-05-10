@echo off
REM 这是一个示例外部批处理程序
REM 它会回显所有传递给它的参数，或者在没有参数时显示一条消息。

if "%~1"=="" (
    echo [BAT_OUTPUT] 没有提供参数给批处理文件。这是来自 example_external_app.bat 的默认消息。
) else (
    echo [BAT_OUTPUT] 批处理文件 example_external_app.bat 收到的参数如下:
    echo %*
)