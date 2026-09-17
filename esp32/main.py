import network
import asyncio
import json
import time
import machine
import socket

from machine import Pin, ADC
from ws import AsyncWebsocketClient


# ==========================================
# HARDWARE
# ==========================================

ldr = ADC(Pin(34))
ldr.atten(ADC.ATTN_11DB)

led = Pin(2, Pin.OUT)
led.value(0)


# ==========================================
# CONFIGURACION
# ==========================================

ARCHIVO_CONFIG = "config.json"

TIEMPO_REINTENTO = 3
TIMEOUT_HEARTBEAT = 7000

wifi = network.WLAN(network.STA_IF)
wifi.active(True)

ultimo_pong = 0


# ==========================================
# CARGAR CONFIGURACION
# ==========================================

def cargar_config():

    try:

        with open(
            ARCHIVO_CONFIG,
            "r"
        ) as archivo:

            config = json.load(
                archivo
            )


        if (
            config.get("ssid")
            and
            config.get("password") is not None
            and
            config.get("websocket")
            and
            config.get("token")
        ):

            return config


    except Exception as error:

        print(
            "Sin configuracion:",
            error
        )


    return None


# ==========================================
# GUARDAR CONFIGURACION
# ==========================================

def guardar_config(
    ssid,
    password,
    websocket,
    token
):

    config = {

        "ssid": ssid,

        "password": password,

        "websocket": websocket,

        "token": token

    }


    with open(
        ARCHIVO_CONFIG,
        "w"
    ) as archivo:

        json.dump(
            config,
            archivo
        )


# ==========================================
# URL DECODE
# ==========================================

def url_decode(texto):

    texto = texto.replace(
        "+",
        " "
    )

    resultado = ""

    i = 0


    while i < len(texto):

        if (
            texto[i] == "%"
            and
            i + 2 < len(texto)
        ):

            try:

                resultado += chr(
                    int(
                        texto[
                            i + 1:
                            i + 3
                        ],
                        16
                    )
                )

                i += 3

                continue

            except:
                pass


        resultado += texto[i]

        i += 1


    return resultado


def obtener_campos(cuerpo):

    campos = {}


    for elemento in cuerpo.split("&"):

        if "=" in elemento:

            clave, valor = (
                elemento.split(
                    "=",
                    1
                )
            )

            campos[
                url_decode(clave)
            ] = url_decode(valor)


    return campos


# ==========================================
# PORTAL CONFIGURACION
# ==========================================

def portal_configuracion():

    print()
    print("==============================")
    print("MODO CONFIGURACION")
    print("==============================")


    wifi.active(False)


    ap = network.WLAN(
        network.AP_IF
    )

    ap.active(True)

    ap.config(
        essid="ESP32-CONFIG"
    )


    while not ap.active():

        time.sleep_ms(100)


    print(
        "Red creada: ESP32-CONFIG"
    )

    print(
        "IP:",
        ap.ifconfig()[0]
    )


    html = """<!DOCTYPE html>
<html lang="es">

<head>

<meta charset="UTF-8">

<meta name="viewport"
content="width=device-width,initial-scale=1">

<title>ESP32 Config</title>

<style>

body{
font-family:Arial;
background:#f4f6f8;
padding:30px;
}

.contenedor{
max-width:500px;
margin:auto;
background:white;
padding:30px;
border-radius:15px;
box-shadow:0 3px 15px #aaa;
}

input{
width:100%;
padding:12px;
margin:8px 0 18px;
box-sizing:border-box;
}

button{
width:100%;
padding:14px;
background:#2563eb;
color:white;
border:0;
border-radius:8px;
font-size:16px;
}

</style>

</head>

<body>

<div class="contenedor">

<h1>ESP32 IoT</h1>

<p>
Configuracion del dispositivo
</p>

<form method="POST">

<label>
Nombre WiFi
</label>

<input
name="ssid"
required>


<label>
Contrasena WiFi
</label>

<input
type="password"
name="password">


<label>
Endpoint WebSocket
</label>

<input
name="websocket"
placeholder="ws://192.168.0.191:8080/"
required>


<label>
Token
</label>

<input
name="token"
placeholder="iot-esp32-01"
required>


<button type="submit">

Guardar configuracion

</button>

</form>

</div>

</body>

</html>"""


    servidor = socket.socket()


    servidor.setsockopt(
        socket.SOL_SOCKET,
        socket.SO_REUSEADDR,
        1
    )


    servidor.bind(
        ("0.0.0.0", 80)
    )


    servidor.listen(1)


    print(
        "Abre http://192.168.4.1"
    )


    while True:

        cliente, direccion = (
            servidor.accept()
        )


        try:

            peticion = (
                cliente.recv(4096)
                .decode()
            )


            if peticion.startswith(
                "POST"
            ):

                partes = (
                    peticion.split(
                        "\r\n\r\n",
                        1
                    )
                )


                if len(partes) == 2:

                    campos = obtener_campos(
                        partes[1]
                    )


                    ssid = campos.get(
                        "ssid",
                        ""
                    )

                    password = campos.get(
                        "password",
                        ""
                    )

                    websocket = campos.get(
                        "websocket",
                        ""
                    )

                    token = campos.get(
                        "token",
                        ""
                    )


                    if (
                        ssid
                        and websocket
                        and token
                    ):

                        guardar_config(
                            ssid,
                            password,
                            websocket,
                            token
                        )


                        respuesta = """HTTP/1.1 200 OK\r
Content-Type: text/html\r
Connection: close\r
\r
<html>
<body style="font-family:Arial;text-align:center;padding:50px">
<h1>Configuracion guardada</h1>
<p>La ESP32 se reiniciara.</p>
</body>
</html>"""


                        cliente.send(
                            respuesta.encode()
                        )

                        cliente.close()

                        time.sleep(2)

                        machine.reset()


            respuesta = (
                "HTTP/1.1 200 OK\r\n"
                "Content-Type: text/html\r\n"
                "Connection: close\r\n"
                "\r\n"
                + html
            )


            cliente.send(
                respuesta.encode()
            )


        except Exception as error:

            print(
                "Error portal:",
                error
            )


        finally:

            try:
                cliente.close()

            except:
                pass


# ==========================================
# WIFI
# ==========================================

async def conectar_wifi(config):

    wifi.active(True)


    if wifi.isconnected():

        print("WiFi conectado")

        print(
            "IP ESP32:",
            wifi.ifconfig()[0]
        )

        return True


    print(
        "Conectando WiFi..."
    )


    wifi.connect(
        config["ssid"],
        config["password"]
    )


    for intento in range(20):

        if wifi.isconnected():

            print(
                "WiFi conectado"
            )

            print(
                "IP ESP32:",
                wifi.ifconfig()[0]
            )

            return True


        print(
            "Esperando WiFi...",
            intento + 1
        )

        await asyncio.sleep(1)


    return False


# ==========================================
# TELEMETRIA
# ==========================================

async def enviar_telemetria(
    ws,
    config
):

    contador = 0


    while True:

        contador += 1


        datos = {

            "tipo":
                "telemetria",

            "id":
                "esp32-01",

            "token":
                config["token"],

            "luz":
                ldr.read(),

            "numero":
                contador

        }


        await ws.send(
            json.dumps(datos)
        )


        print(
            "Luz enviada:",
            datos["luz"]
        )


        await asyncio.sleep(2)


# ==========================================
# RECIBIR MENSAJES
# ==========================================

async def recibir_mensajes(ws):

    global ultimo_pong


    while True:

        mensaje = await ws.recv()


        if mensaje:

            datos = json.loads(
                mensaje
            )


            tipo = datos.get(
                "tipo"
            )


            # ==============================
            # PONG
            # ==============================

            if tipo == "pong":

                ultimo_pong = (
                    time.ticks_ms()
                )

                print(
                    "PONG recibido"
                )


            # ==============================
            # AUTENTICACION
            # ==============================

            elif tipo == "registro_ok":

                print(
                    "ESP32 autenticada"
                )


            # ==============================
            # COMANDO
            # ==============================

            elif tipo == "comando":

                comando = datos.get(
                    "comando"
                )

                comando_id = datos.get(
                    "comando_id"
                )


                if comando == "LED_ON":

                    led.value(1)

                    print(
                        "LED ENCENDIDO"
                    )


                    await ws.send(
                        json.dumps({

                            "tipo":
                                "estado",

                            "id":
                                "esp32-01",

                            "estado_led":
                                "ENCENDIDO",

                            "comando_id":
                                comando_id

                        })
                    )


                elif comando == "LED_OFF":

                    led.value(0)

                    print(
                        "LED APAGADO"
                    )


                    await ws.send(
                        json.dumps({

                            "tipo":
                                "estado",

                            "id":
                                "esp32-01",

                            "estado_led":
                                "APAGADO",

                            "comando_id":
                                comando_id

                        })
                    )


        await asyncio.sleep_ms(50)


# ==========================================
# HEARTBEAT
# ==========================================

async def heartbeat(ws):

    global ultimo_pong

    ultimo_pong = (
        time.ticks_ms()
    )


    while True:

        await asyncio.sleep(3)


        await ws.send(
            json.dumps({
                "tipo": "ping"
            })
        )


        print(
            "PING enviado"
        )


        await asyncio.sleep(2)


        diferencia = (
            time.ticks_diff(
                time.ticks_ms(),
                ultimo_pong
            )
        )


        if (
            diferencia >
            TIMEOUT_HEARTBEAT
        ):

            raise Exception(
                "Timeout heartbeat"
            )


# ==========================================
# SESION WEBSOCKET
# ==========================================

async def sesion_websocket(
    config
):

    ws = AsyncWebsocketClient()


    print(
        "Conectando WebSocket:"
    )

    print(
        config["websocket"]
    )


    await ws.handshake(
        config["websocket"]
    )


    print(
        "WebSocket conectado"
    )


    await ws.send(
        json.dumps({

            "tipo":
                "registro",

            "dispositivo":
                "esp32",

            "id":
                "esp32-01",

            "token":
                config["token"]

        })
    )


    t1 = asyncio.create_task(
        enviar_telemetria(
            ws,
            config
        )
    )


    t2 = asyncio.create_task(
        recibir_mensajes(ws)
    )


    t3 = asyncio.create_task(
        heartbeat(ws)
    )


    try:

        await asyncio.gather(
            t1,
            t2,
            t3
        )


    finally:

        t1.cancel()
        t2.cancel()
        t3.cancel()


        try:
            await ws.close()

        except:
            pass


# ==========================================
# MAIN
# ==========================================

async def main():

    config = cargar_config()


    if config is None:

        portal_configuracion()

        return


    print()
    print("==============================")
    print(" SISTEMA IoT ESP32")
    print("==============================")
    print("Configuracion encontrada")
    print(
        "SSID:",
        config["ssid"]
    )
    print(
        "WebSocket:",
        config["websocket"]
    )
    print("==============================")


    while True:

        conectado = (
            await conectar_wifi(
                config
            )
        )


        if not conectado:

            print(
                "Reintentando WiFi..."
            )

            await asyncio.sleep(
                TIEMPO_REINTENTO
            )

            continue


        try:

            await sesion_websocket(
                config
            )


        except Exception as error:

            print()
            print("==============================")
            print("CONEXION PERDIDA")
            print("==============================")

            print(
                "Error:",
                error
            )


        await asyncio.sleep(
            TIEMPO_REINTENTO
        )


# ==========================================
# INICIO
# ==========================================

config_inicio = cargar_config()


if config_inicio is None:

    portal_configuracion()

else:

    asyncio.run(
        main()
    )