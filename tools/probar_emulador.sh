#!/usr/bin/env bash
# Instala el APK en un emulador Android, lo abre y guarda captura de pantalla + registros.
# Es solo una verificación: no bloquea la entrega del APK.
set -u
mkdir -p diagnostico

APK=$(ls apk/*.apk 2>/dev/null | head -n1)
echo "APK: ${APK:-no encontrado}" | tee diagnostico/resumen.txt
[ -z "${APK}" ] && exit 0

adb install -r "$APK" 2>&1 | tee diagnostico/instalacion.txt

PKG=$(adb shell pm list packages | grep -i dulce | head -n1 | cut -d: -f2 | tr -d '\r')
echo "Paquete: ${PKG:-no encontrado}" | tee -a diagnostico/resumen.txt
[ -z "${PKG}" ] && exit 0

adb logcat -c
adb shell monkey -p "$PKG" -c android.intent.category.LAUNCHER 1 2>&1 | tee -a diagnostico/resumen.txt

# Capturas a los 20 y 60 segundos (la primera apertura descomprime Python y tarda)
sleep 20
adb exec-out screencap -p > diagnostico/pantalla_20s.png
sleep 40
adb exec-out screencap -p > diagnostico/pantalla_60s.png

adb logcat -d > diagnostico/logcat_completo.txt
grep -iE "python|flet|serious|FATAL|AndroidRuntime|Traceback|Exception" \
  diagnostico/logcat_completo.txt > diagnostico/logcat_filtrado.txt || true
echo "Listo. Revisa la carpeta diagnostico." | tee -a diagnostico/resumen.txt
