

import pymysql
from pymysql.cursors import DictCursor

from config import MYSQL_CONFIG


class ConexionMySQL:

    def __init__(self, config=None):
        self.config = config or MYSQL_CONFIG
        self.conexion = None

    def conectar(self):
        try:
            self.conexion = pymysql.connect(
                **self.config,
                cursorclass=DictCursor,  # cada fila llega como diccionario
            )
            return self.conexion
        except pymysql.MySQLError as error:
            self.conexion = None
            raise ConnectionError(f"No se pudo conectar a MySQL: {error}") from error

    def ejecutar_consulta(self, sql, parametros=None):

        if self.conexion is None:
            raise ConnectionError("No hay conexión activa con MySQL. Llame a conectar().")

        cursor = None
        try:
            cursor = self.conexion.cursor()
            cursor.execute(sql, parametros)
            return cursor.fetchall()
        except pymysql.MySQLError as error:
            raise RuntimeError(f"Error al ejecutar la consulta: {error}") from error
        finally:
            if cursor is not None:
                cursor.close()

    def cerrar(self):
        if self.conexion is not None:
            self.conexion.close()
            self.conexion = None

    def __enter__(self):
        self.conectar()
        return self

    def __exit__(self, tipo_error, valor_error, traza):
        self.cerrar()
        return False


if __name__ == "__main__":
    try:
        with ConexionMySQL() as bd:
            version = bd.ejecutar_consulta("SELECT VERSION() AS version")
            print("Versión de MySQL:", version[0]["version"])

            categorias = bd.ejecutar_consulta("SELECT COUNT(*) AS total FROM categories")
            print("Categorías:", categorias[0]["total"])

            pedidos = bd.ejecutar_consulta("SELECT COUNT(*) AS total FROM orders")
            print("Pedidos:", pedidos[0]["total"])

            normal = bd.ejecutar_consulta(
                "SELECT OrderID, ShippedDate FROM orders WHERE OrderID = %s", (10248,)
            )
            print("Pedido 10248:", normal[0])

            cero = bd.ejecutar_consulta(
                "SELECT OrderID, ShippedDate FROM orders WHERE OrderID = %s", (11008,)
            )
            print("Pedido 11008:", cero[0], "| tipo:", type(cero[0]["ShippedDate"]).__name__)
    except (ConnectionError, RuntimeError) as error:
        print("ERROR:", error)