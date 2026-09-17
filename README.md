# Sistema IoT Bidireccional con ESP32 y WebSocket

## Descripción

Este proyecto implementa un sistema IoT de comunicación bidireccional utilizando un ESP32, un sensor LDR, un actuador LED y el protocolo WebSocket.

El sistema permite enviar telemetría desde el ESP32 hacia un servidor en tiempo real y, al mismo tiempo, enviar comandos desde una interfaz web hacia el dispositivo para controlar un LED.

Además, se implementaron mecanismos de autenticación, heartbeat, detección de pérdida de conexión, reconexión automática y aprovisionamiento de parámetros de red.

Como parte de la evaluación del sistema se realizó una comparación experimental entre WebSocket y una línea base basada en HTTP Polling.

---

## Objetivo

Construir un canal de telemetría bidireccional para un dispositivo IoT mediante WebSocket, buscando:

- Reducir el tráfico generado frente a una línea base de sondeo HTTP.
- Permitir comunicación bidireccional en tiempo real.
- Medir la latencia de los comandos.
- Detectar pérdidas de conexión.
- Recuperar automáticamente la comunicación.
- Permitir configurar Wi-Fi, endpoint y credenciales sin modificar el código fuente del dispositivo.

---

## Arquitectura del sistema

La arquitectura implementada es la siguiente:

```text
                  TELEMETRÍA
                     ──────►

┌─────────┐     ┌─────────┐      WebSocket      ┌────────────┐
│   LDR   │────►│  ESP32  │◄──────────────────►│  Servidor  │
└─────────┘     └────┬────┘                     └─────┬──────┘
                     │                                │
                     │ GPIO 2                         │ WebSocket
                     ▼                                │
                 ┌───────┐                            ▼
                 │  LED  │                     ┌─────────────┐
                 └───────┘                     │  Dashboard  │
                                               │     Web     │
                                               └─────────────┘

                     ◄──────
                      CONTROL
```

El LDR genera las lecturas de iluminación.

El ESP32 procesa la lectura ADC y la transmite al servidor mediante una conexión WebSocket persistente.

El servidor recibe la telemetría y la distribuye hacia el dashboard.

La comunicación también funciona en sentido contrario, permitiendo que el usuario envíe comandos desde el navegador para encender o apagar el LED conectado al ESP32.

---

## Tecnologías utilizadas

### Hardware

- ESP32-WROOM-32
- Sensor LDR
- Resistencia para divisor de voltaje
- LED integrado del ESP32 (GPIO 2)
- Protoboard
- Cables de conexión

### Software

- MicroPython
- Python
- WebSocket
- HTML
- CSS
- JavaScript
- Visual Studio Code
- Thonny
- Navegador web

### Librerías

Servidor Python:

```text
websockets==17.1
```

ESP32:

```python
from ws import AsyncWebsocketClient
```

---

## Conexión del sensor LDR

El LDR se conectó mediante un divisor de voltaje.

```text
3.3 V
  │
  │
 LDR
  │
  ├──────── GPIO 34
  │
Resistencia
  │
  │
 GND
```

El GPIO 34 se utiliza como entrada ADC.

La lectura del sensor se realiza mediante:

```python
ldr = ADC(Pin(34))
ldr.atten(ADC.ATTN_11DB)
```

El valor ADC utilizado por la interfaz se encuentra en un rango de referencia de:

```text
0 - 4095
```

El porcentaje mostrado en el dashboard representa un nivel relativo respecto al ADC y no una medición calibrada en lux.

---

## Comunicación WebSocket

El ESP32 mantiene una conexión WebSocket persistente con el servidor.

Ejemplo de endpoint:

```text
ws://IP_DEL_SERVIDOR:8080/
```

Una vez establecida la conexión, el dispositivo transmite periódicamente la lectura del LDR.

Ejemplo de mensaje:

```json
{
    "tipo": "telemetria",
    "id": "esp32-01",
    "token": "TOKEN_DEL_DISPOSITIVO",
    "luz": 667,
    "numero": 31
}
```

La frecuencia utilizada durante las pruebas fue aproximadamente:

```text
1 lectura cada 2 segundos
```

---

## Comunicación bidireccional

Además de recibir telemetría, WebSocket permite enviar comandos desde el dashboard hacia el ESP32 utilizando la misma conexión.

Ejemplo:

```json
{
    "tipo": "comando",
    "comando": "LED_ON",
    "comando_id": "cmd-001"
}
```

El servidor reenvía el comando al ESP32.

El dispositivo modifica el GPIO 2 y devuelve una confirmación:

```json
{
    "tipo": "estado",
    "id": "esp32-01",
    "estado_led": "ENCENDIDO",
    "comando_id": "cmd-001"
}
```

El mismo mecanismo se utiliza para apagar el LED mediante:

```text
LED_OFF
```

---

## Autenticación

El dispositivo utiliza un token durante su registro con el servidor.

El servidor valida las credenciales antes de aceptar al ESP32 como dispositivo autorizado.

Por seguridad, las credenciales reales no deben almacenarse en el repositorio.

El archivo:

```text
esp32/config.example.json
```

muestra únicamente la estructura necesaria:

```json
{
    "ssid": "NOMBRE_DE_TU_WIFI",
    "password": "CONTRASENA_DE_TU_WIFI",
    "websocket": "ws://IP_DEL_SERVIDOR:8080/",
    "token": "TOKEN_DEL_DISPOSITIVO"
}
```

El archivo real `config.json` se excluye mediante `.gitignore`.

---

## Aprovisionamiento

El ESP32 puede almacenar su configuración en:

```text
config.json
```

Los parámetros utilizados son:

- SSID de la red Wi-Fi.
- Contraseña Wi-Fi.
- Endpoint WebSocket.
- Token del dispositivo.

Cuando no existe una configuración almacenada, el ESP32 crea temporalmente un punto de acceso:

```text
ESP32-CONFIG
```

La interfaz de configuración se encuentra localmente en:

```text
http://192.168.4.1
```

Desde esta interfaz pueden introducirse los parámetros de conexión sin modificar directamente las constantes del código fuente.

Después de guardar la configuración, el ESP32 se reinicia y utiliza los parámetros almacenados.

---

## Heartbeat

Para detectar pérdidas de comunicación se implementó un heartbeat a nivel de aplicación.

El ESP32 envía periódicamente:

```json
{
    "tipo": "ping"
}
```

El servidor responde:

```json
{
    "tipo": "pong"
}
```

El ESP32 registra la recepción de la respuesta.

Si deja de recibir respuestas dentro del tiempo configurado, considera que la conexión se perdió y comienza el proceso de recuperación.

---

## Reconexión automática

El sistema incluye mecanismos de recuperación frente a pérdidas de comunicación.

Se realizaron pruebas desconectando temporalmente:

- El servidor WebSocket.
- La conexión Wi-Fi.

El ESP32 detectó la pérdida de comunicación y realizó nuevos intentos de conexión.

Cuando el servicio o la red volvieron a estar disponibles, el dispositivo recuperó la comunicación sin necesidad de reiniciar manualmente el programa.

El dashboard también realiza intentos de reconexión al servidor cuando pierde su conexión WebSocket.

---

# Evaluación experimental

## Línea base HTTP Polling

Para comparar el tráfico generado se implementó una línea base utilizando HTTP Polling.

El navegador realiza una solicitud HTTP periódicamente:

```text
GET /telemetria
```

La frecuencia configurada fue aproximadamente:

```text
1 solicitud cada 2 segundos
```

La prueba se ejecutó durante 60 segundos.

### Resultado HTTP

```text
Solicitudes: 31
Duración: 60.0 segundos
Tráfico estimado: 6656 bytes
```

La línea base utiliza un valor ADC simulado para mantener una prueba controlada del mecanismo de sondeo.

---

## Prueba WebSocket

Se ejecutó la transmisión de telemetría mediante WebSocket durante aproximadamente el mismo periodo.

### Resultado WebSocket

```text
Mensajes: 31
Duración: 60.5 segundos
Tráfico estimado: 2998 bytes
```

---

## Comparación de tráfico

| Protocolo | Intercambios | Duración | Tráfico estimado |
|---|---:|---:|---:|
| HTTP Polling | 31 | 60.0 s | 6656 bytes |
| WebSocket | 31 | 60.5 s | 2998 bytes |

La reducción observada se calculó mediante:

```text
Reducción = ((HTTP - WebSocket) / HTTP) × 100
```

Sustituyendo los valores:

```text
Reducción = ((6656 - 2998) / 6656) × 100
```

Resultado:

```text
54.96 %
```

En las condiciones específicas del experimento, WebSocket presentó aproximadamente un **54.96 % menos bytes contabilizados** que la línea base HTTP Polling.

Los valores corresponden a la estimación realizada a nivel de aplicación/protocolo durante el experimento y no representan una captura del total de bytes físicos transmitidos por la interfaz Wi-Fi.

---

# Medición de latencia

La latencia se midió desde el dashboard utilizando el recorrido:

```text
Dashboard
   │
   ▼
Servidor WebSocket
   │
   ▼
ESP32
   │
   ▼
Cambio del LED
   │
   ▼
Confirmación
   │
   ▼
Servidor
   │
   ▼
Dashboard
```

Cada comando utiliza un identificador único denominado:

```text
comando_id
```

El navegador registra el tiempo al enviar el comando y calcula la diferencia cuando recibe la confirmación correspondiente del ESP32.

Esto permite medir el tiempo extremo a extremo sin necesitar sincronizar el reloj del ESP32 con el reloj de la computadora.

## Resultados de latencia

Se realizaron 20 mediciones.

| Métrica | Resultado |
|---|---:|
| Número de muestras | 20 |
| Latencia promedio | 285.38 ms |
| Latencia mínima | 123.10 ms |
| Latencia máxima | 486.70 ms |

La medición corresponde al recorrido completo de un comando y su confirmación, no únicamente al tiempo de propagación de un paquete en la red.

---

# Dashboard

La interfaz web permite visualizar:

- Estado de conexión con el servidor.
- Estado de conexión del ESP32.
- Lectura ADC del LDR.
- Nivel relativo de iluminación.
- Historial de telemetría.
- Estado del LED.
- Encendido remoto del LED.
- Apagado remoto del LED.
- Latencia del último comando.
- Latencia promedio.
- Latencia mínima.
- Latencia máxima.
- Número de mediciones realizadas.

---

# Estructura del proyecto

```text
IOT-WebSocket-LDR/
│
├── esp32/
│   ├── main.py
│   └── config.example.json
│
├── server/
│   ├── servidor.py
│   └── requirements.txt
│
├── web/
│   ├── index.html
│   └── polling.html
│
├── baseline-http/
│   └── baseline_http.py
│
├── evidencias/
│   └── capturas de las pruebas
│
├── .gitignore
└── README.md
```

---

# Instalación

## 1. Clonar el repositorio

```bash
git clone URL_DEL_REPOSITORIO
```

Entrar al proyecto:

```bash
cd IOT-WebSocket-LDR
```

---

## 2. Crear entorno virtual

En Windows:

```powershell
python -m venv .venv
```

Activar:

```powershell
.\.venv\Scripts\Activate.ps1
```

Si PowerShell bloquea temporalmente la ejecución:

```powershell
Set-ExecutionPolicy -Scope Process -ExecutionPolicy Bypass
```

Después:

```powershell
.\.venv\Scripts\Activate.ps1
```

---

## 3. Instalar dependencias

```powershell
pip install -r server/requirements.txt
```

---

## 4. Ejecutar servidor

Desde la raíz del proyecto:

```powershell
python server/servidor.py
```

El servidor utiliza el puerto:

```text
8080
```

---

## 5. Configurar ESP32

El ESP32 debe tener MicroPython instalado.

También debe encontrarse disponible la librería:

```text
lib/ws.py
```

correspondiente al cliente WebSocket asíncrono utilizado por el proyecto.

El archivo:

```text
esp32/main.py
```

debe copiarse al dispositivo como:

```text
/main.py
```

La configuración privada del dispositivo se almacena en:

```text
/config.json
```

---

## 6. Abrir dashboard

Abrir:

```text
web/index.html
```

El endpoint WebSocket configurado en el dashboard debe corresponder con la dirección IP de la computadora donde se está ejecutando el servidor.

Ejemplo:

```text
ws://192.168.X.X:8080/
```

---

# Línea base HTTP

Para ejecutar la prueba HTTP:

```powershell
python baseline-http/baseline_http.py
```

Después abrir:

```text
web/polling.html
```

La prueba realiza solicitudes periódicas para representar una arquitectura basada en sondeo HTTP.

---

# Evidencias

La carpeta:

```text
evidencias/
```

contiene las capturas obtenidas durante las pruebas del proyecto, incluyendo evidencias relacionadas con:

- Funcionamiento del dashboard.
- Lectura del LDR.
- Control bidireccional del LED.
- Medición de latencia.
- Línea base HTTP.
- Tráfico WebSocket.
- Heartbeat.
- Pérdida y recuperación de conexión.
- Aprovisionamiento del ESP32.

---

# Resultados principales

El prototipo permitió establecer comunicación bidireccional entre un ESP32 y una interfaz de monitoreo mediante una conexión WebSocket persistente.

Durante las pruebas realizadas se obtuvieron los siguientes resultados:

```text
HTTP Polling:
6656 bytes estimados / 31 solicitudes / 60.0 s

WebSocket:
2998 bytes estimados / 31 mensajes / 60.5 s

Reducción observada:
54.96 %

Latencia WebSocket extremo a extremo:
Promedio: 285.38 ms
Mínima:   123.10 ms
Máxima:   486.70 ms
Muestras: 20
```

Además, se comprobó el funcionamiento de la detección de pérdida de comunicación y la recuperación automática después de restablecer el servidor o la conexión Wi-Fi.

---

# Conclusiones

La implementación permitió construir un canal de comunicación bidireccional entre un dispositivo IoT y una interfaz de monitoreo utilizando WebSocket.

En la prueba experimental realizada, WebSocket redujo los bytes contabilizados frente a la línea base HTTP Polling bajo una frecuencia de intercambio comparable.

La conexión persistente también permitió utilizar el mismo canal para transmitir telemetría y recibir comandos de control.

La medición extremo a extremo permitió cuantificar el tiempo requerido para enviar un comando desde el dashboard, procesarlo en el ESP32 y recibir su confirmación.

Finalmente, el uso de heartbeat, reconexión automática y almacenamiento de parámetros de configuración proporciona mecanismos para detectar interrupciones, recuperar la comunicación y facilitar el aprovisionamiento del dispositivo sin modificar directamente las credenciales dentro del código fuente.

---

## Autor

**Gustavo Emilio Fernández Sánchez**

Ingeniería en Tecnologías de la Información y Comunicaciones