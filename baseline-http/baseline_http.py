from http.server import BaseHTTPRequestHandler, HTTPServer
import json
import time

contador = 0
bytes_aplicacion = 0
inicio = None


class Handler(BaseHTTPRequestHandler):

    def do_GET(self):

        global contador
        global bytes_aplicacion
        global inicio

        if self.path == "/telemetria":

            if inicio is None:
                inicio = time.time()

            contador += 1

            datos = {
                "tipo": "telemetria",
                "id": "esp32-01",
                "luz": 650,
                "numero": contador
            }

            cuerpo = json.dumps(datos).encode()

            # Aproximación del tamaño de solicitud HTTP
            solicitud = (
                f"GET /telemetria HTTP/1.1\r\n"
                f"Host: 192.168.0.191:8081\r\n"
                f"Connection: keep-alive\r\n\r\n"
            ).encode()

            # Encabezados de respuesta que enviamos
            encabezados = (
                "HTTP/1.1 200 OK\r\n"
                "Content-Type: application/json\r\n"
                f"Content-Length: {len(cuerpo)}\r\n"
                "\r\n"
            ).encode()

            bytes_peticion = len(solicitud)
            bytes_respuesta = len(encabezados) + len(cuerpo)

            bytes_aplicacion += (
                bytes_peticion +
                bytes_respuesta
            )

            self.send_response(200)

            self.send_header(
                "Access-Control-Allow-Origin",
                "*"
            )

            self.send_header(
                "Content-Length",
                str(len(cuerpo))
            )

            self.end_headers()

            self.wfile.write(cuerpo)

            tiempo = time.time() - inicio

            print(
                f"HTTP #{contador} | "
                f"{bytes_peticion + bytes_respuesta} bytes | "
                f"Total: {bytes_aplicacion} bytes | "
                f"Tiempo: {tiempo:.1f}s"
            )

        elif self.path == "/resultados":

            resultado = {
                "solicitudes": contador,
                "bytes_estimados_aplicacion":
                    bytes_aplicacion,
                "tiempo":
                    round(
                        time.time() - inicio,
                        2
                    )
                    if inicio else 0
            }

            cuerpo = json.dumps(
                resultado,
                indent=4
            ).encode()

            self.send_response(200)

            self.send_header(
                "Access-Control-Allow-Origin",
                "*"
            )

            self.send_header(
                "Content-Length",
                str(len(cuerpo))
            )

            self.end_headers()

            self.wfile.write(cuerpo)

        else:

            self.send_response(404)
            self.end_headers()


    # Para que la consola quede limpia
    def log_message(
        self,
        format,
        *args
    ):
        return


print("==============================")
print(" LINEA BASE HTTP POLLING")
print("==============================")
print("Puerto: 8081")
print("Endpoint:")
print(
    "http://192.168.0.191:8081/telemetria"
)
print("==============================")


servidor = HTTPServer(
    ("0.0.0.0", 8081),
    Handler
)

servidor.serve_forever()