@echo off
title AIDEN - Asistente
REM La ruta sale de DONDE ESTA ESTE .bat (%~dp0), no escrita a mano. La version anterior tenia
REM clavada "c:\Users\Usuario\Desktop\Python Proyecto\SLIDE-AI-BUTLER" y el entorno
REM "Asistente_Slide_311": ninguno de los dos existe en esta PC, asi que el lanzador estaba roto
REM aqui y nadie lo habia notado porque se arranca desde VS Code.
cd /d "%~dp0"

REM El entorno virtual, se llame como se llame en cada PC.
if exist "Asistente\Scripts\activate.bat" call "Asistente\Scripts\activate.bat"
if exist "Asistente_Slide_311\Scripts\activate.bat" call "Asistente_Slide_311\Scripts\activate.bat"

REM Arranca el SUPERVISOR, no AIDEN directo: el supervisor lanza Main_AlwaysOn.py y lo relanza si
REM se cae o se congela. El candado de instancia unica sigue siendo el de AIDEN (puerto 50607);
REM el supervisor usa el 50608 para no competir por el suyo.
python Nucleo_Slide\Supervisor.py >> AIDEN_log.txt 2>&1
