
from pymongo import MongoClient
from pymongo.errors import PyMongoError

from config import MONGO_URI, MONGO_DB


class ConexionMongo:

    def __init__(self, uri=None, nombre_bd=None):
        self.uri = uri or MONGO_URI
        self.nombre_bd = nombre_bd or MONGO_DB
        self.cliente = None
        self.bd = None

    def conectar(self):
        try:
            self.cliente = MongoClient(self.uri, serverSelectionTimeoutMS=5000)
            self.cliente.admin.command("ping")
            self.bd = self.cliente[self.nombre_bd]
            return self.bd
        except PyMongoError as error:
            self.cerrar()
            raise ConnectionError(f"No se pudo conectar a MongoDB: {error}") from error

    def cerrar(self):
        if self.cliente is not None:
            self.cliente.close()
        self.cliente = None
        self.bd = None

    def __enter__(self):
        self.conectar()
        return self

    def __exit__(self, tipo_error, valor_error, traza):
        self.cerrar()
        return False


if __name__ == "__main__":
    try:
        with ConexionMongo() as mongo:
            info = mongo.cliente.server_info()
            print("Versión de MongoDB:", info["version"])
            print("Base de datos de trabajo:", mongo.bd.name)
            print("Colecciones actuales:", mongo.bd.list_collection_names())
    except ConnectionError as error:
        print("ERROR:", error)