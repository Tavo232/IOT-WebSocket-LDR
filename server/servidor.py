import asyncio
import json
import time
import websockets
from datetime import datetime


# ==========================================
# CONFIGURACION
# ==========================================

TOKEN_VALIDO = "iot-esp32-01"

esp32 = None
navegadores = set()

ultimo_dato = None
ultimo_estado_led = "DESCONOCIDO"


# ==========================================
# MEDICION DE TRAFICO WEBSOCKET
# ==========================================

bytes_websocket = 0
mensajes_websocket = 0
inicio_medicion = None


# ==========================================
# ENVIAR A NAVEGADORES
# ==========================================

async def enviar_navegadores(datos):

    if not navegadores:
        return

    mensaje = json.dumps(datos)

    muertos = []

    for navegador in navegadores:

        try:
            await navegador.send(mensaje)

        except Exception:
            muertos.append(navegador)

    for navegador in muertos:
        navegadores.discard(navegador)


# ==========================================
# MANEJAR CLIENTES
# ==========================================

async def manejar_cliente(websocket):

    global esp32
    global ultimo_dato
    global ultimo_estado_led

    global bytes_websocket
    global mensajes_websocket
    global inicio_medicion

    print("\nNueva conexion")

    try:

        async for mensaje in websocket:

            try:
                datos = json.loads(mensaje)

            except json.JSONDecodeError:

                print("JSON no valido")
                continue

            tipo = datos.get("tipo")


            # ==================================
            # HEARTBEAT
            # ==================================

            if tipo == "ping":

                await websocket.send(
                    json.dumps({
                        "tipo": "pong"
                    })
                )


            # ==================================
            # REGISTRO ESP32
            # ==================================

            elif tipo == "registro":

                if datos.get("dispositivo") == "esp32":

                    token = datos.get("token")

                    if token != TOKEN_VALIDO:

                        print(
                            "ESP32 rechazada: token incorrecto"
                        )

                        await websocket.send(
                            json.dumps({
                                "tipo": "autenticacion_error"
                            })
                        )

                        await websocket.close()
                        return

                    esp32 = websocket

                    print("========================")
                    print("ESP32 AUTENTICADA")
                    print("========================")

                    await websocket.send(
                        json.dumps({
                            "tipo": "registro_ok"
                        })
                    )

                    await enviar_navegadores({
                        "tipo": "conexion_esp32",
                        "estado": "CONECTADA"
                    })


            # ==================================
            # TELEMETRIA
            # ==================================

            elif tipo == "telemetria":

                if websocket != esp32:
                    continue

                if datos.get("token") != TOKEN_VALIDO:
                    continue


                # ==================================
                # CONTADOR DE TRAFICO WEBSOCKET
                # ==================================

                if inicio_medicion is None:
                    inicio_medicion = time.time()


                # Tamaño real del JSON recibido
                bytes_payload = len(
                    mensaje.encode("utf-8")
                )


                # Frame WebSocket:
                # 2 bytes de cabecera
                # + 4 bytes de mascara
                bytes_frame = bytes_payload + 6


                bytes_websocket += bytes_frame

                mensajes_websocket += 1


                tiempo_transcurrido = (
                    time.time()
                    - inicio_medicion
                )


                # ==================================
                # DATOS DE TELEMETRIA
                # ==================================

                hora = datetime.now().strftime(
                    "%H:%M:%S"
                )

                datos["hora"] = hora

                ultimo_dato = datos


                print(
                    "Luz:",
                    datos.get("luz"),
                    "| #",
                    datos.get("numero"),
                    "|",
                    hora
                )


                print(
                    f"WS #{mensajes_websocket} | "
                    f"{bytes_frame} bytes | "
                    f"Total: {bytes_websocket} bytes | "
                    f"Tiempo: {tiempo_transcurrido:.1f}s"
                )


                await enviar_navegadores(
                    datos
                )


            # ==================================
            # NAVEGADOR
            # ==================================

            elif tipo == "navegador":

                navegadores.add(
                    websocket
                )

                print(
                    "Dashboard conectado"
                )


                await websocket.send(
                    json.dumps({
                        "tipo": "navegador_ok"
                    })
                )


                if ultimo_dato:

                    await websocket.send(
                        json.dumps(
                            ultimo_dato
                        )
                    )


                await websocket.send(
                    json.dumps({
                        "tipo": "estado",
                        "estado_led":
                            ultimo_estado_led
                    })
                )


                await websocket.send(
                    json.dumps({
                        "tipo": "conexion_esp32",
                        "estado":
                            "CONECTADA"
                            if esp32
                            else "DESCONECTADA"
                    })
                )


            # ==================================
            # COMANDO DEL DASHBOARD
            # ==================================

            elif tipo == "comando":

                if esp32:

                    comando = datos.get(
                        "comando"
                    )

                    comando_id = datos.get(
                        "comando_id"
                    )


                    print(
                        "Comando:",
                        comando,
                        "| ID:",
                        comando_id
                    )


                    await esp32.send(
                        json.dumps({
                            "tipo": "comando",
                            "comando": comando,
                            "comando_id": comando_id
                        })
                    )


                else:

                    await websocket.send(
                        json.dumps({
                            "tipo": "error",
                            "mensaje":
                                "ESP32 desconectada"
                        })
                    )


            # ==================================
            # CONFIRMACION DEL LED
            # ==================================

            elif tipo == "estado":

                # Solo aceptar estados provenientes
                # de la ESP32 autenticada
                if websocket != esp32:
                    continue

                ultimo_estado_led = datos.get(
                    "estado_led"
                )


                print(
                    "LED:",
                    ultimo_estado_led,
                    "| ID:",
                    datos.get("comando_id")
                )


                await enviar_navegadores(
                    datos
                )


    except websockets.exceptions.ConnectionClosed:
        pass


    except Exception as error:

        print(
            "Error:",
            error
        )


    finally:

        navegadores.discard(
            websocket
        )


        if websocket == esp32:

            esp32 = None

            print(
                "ESP32 DESCONECTADA"
            )


            await enviar_navegadores({
                "tipo": "conexion_esp32",
                "estado": "DESCONECTADA"
            })


# ==========================================
# SERVIDOR
# ==========================================

async def main():

    print("==============================")
    print(" SERVIDOR IoT WEBSOCKET")
    print("==============================")
    print("Puerto: 8080")
    print("Autenticacion: ACTIVADA")
    print("Heartbeat: ACTIVADO")
    print("Latencia: ACTIVADA")
    print("Medicion trafico: ACTIVADA")
    print("==============================")


    async with websockets.serve(
        manejar_cliente,
        "0.0.0.0",
        8080
    ):

        await asyncio.Future()


asyncio.run(main())