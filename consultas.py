
from bson import Decimal128

from conexion_mongo import ConexionMongo

def _d128_a_float(valor):
    """Convierte Decimal128 a float para aritmética. Devuelve 0.0 si es None."""
    if isinstance(valor, Decimal128):
        return float(valor.to_decimal())
    if valor is None:
        return 0.0
    return float(valor)

def consulta1_categorias_y_productos():

    print("\n" + "=" * 65)
    print(" CONSULTA 1: Categorías y sus productos")
    print("=" * 65)

    with ConexionMongo() as mongo:
        categorias = list(
            mongo.bd["categories"].find({}, {"_id": 1, "CategoryName": 1})
            .sort("CategoryName", 1)
        )

        productos_raw = list(
            mongo.bd["products"].find(
                {},
                {"_id": 1, "ProductName": 1, "CategoryID": 1}
            ).sort("ProductName", 1)
        )

    productos_por_cat = {}
    for p in productos_raw:
        cid = p["CategoryID"]
        productos_por_cat.setdefault(cid, []).append(p)

    for cat in categorias:
        cid  = cat["_id"]
        nombre_cat = cat["CategoryName"]
        prods = productos_por_cat.get(cid, [])
        print(f"\n  [{cid}] {nombre_cat}  ({len(prods)} productos)")
        print(f"  {'Código':>8}  {'Nombre del producto'}")
        print(f"  {'-'*8}  {'-'*35}")
        for p in prods:
            print(f"  {p['_id']:>8}  {p['ProductName']}")

    print()



def consulta2_inventario_categoria(nombre_categoria: str):

    print("\n" + "=" * 75)
    print(f" CONSULTA 2: Inventario de la categoría '{nombre_categoria}'")
    print("=" * 75)

    with ConexionMongo() as mongo:
        cat = mongo.bd["categories"].find_one(
            {"CategoryName": {"$regex": f"^{nombre_categoria}$", "$options": "i"}},
            {"_id": 1, "CategoryName": 1}
        )
        if not cat:
            print(f"\n  Categoría '{nombre_categoria}' no encontrada.\n")
            return

        cid = cat["_id"]

        productos = list(
            mongo.bd["products"].find(
                {"CategoryID": cid},
                {"_id": 1, "ProductName": 1, "SupplierID": 1,
                 "UnitPrice": 1, "UnitsInStock": 1}
            ).sort("ProductName", 1)
        )

        if not productos:
            print(f"\n  No hay productos para la categoría '{nombre_categoria}'.\n")
            return

        supplier_ids = list({p["SupplierID"] for p in productos if p.get("SupplierID")})
        proveedores_raw = mongo.bd["suppliers"].find(
            {"_id": {"$in": supplier_ids}},
            {"_id": 1, "CompanyName": 1}
        )
        proveedores = {s["_id"]: s["CompanyName"] for s in proveedores_raw}

    print(f"\n  {'Producto':<35} {'Proveedor':<28} {'Precio':>9} {'Stock':>6} {'Total línea':>12}")
    print(f"  {'-'*35} {'-'*28} {'-'*9} {'-'*6} {'-'*12}")

    total_acumulado = 0.0
    for p in productos:
        precio    = _d128_a_float(p.get("UnitPrice"))
        stock     = p.get("UnitsInStock") or 0
        total_lin = precio * stock
        total_acumulado += total_lin
        proveedor = proveedores.get(p.get("SupplierID"), "—")

        print(f"  {p['ProductName']:<35} {proveedor:<28} "
              f"{precio:>9.2f} {stock:>6} {total_lin:>12.2f}")

    print(f"\n  {'Total acumulado de la categoría':>{35+28+9+6+5}} "
          f"{total_acumulado:>12.2f}")
    print()



def consulta3_factura(order_id: int):

    print("\n" + "=" * 65)
    print(f" CONSULTA 3: Factura del pedido #{order_id}")
    print("=" * 65)

    pipeline = [
        {"$match": {"_id": order_id}},
        {"$project": {
            "_id":         1,
            "OrderDate":   1,
            "ShippedDate": 1,
            "Freight":     1,
            "ShipName":    1,
            "ShipCity":    1,
            "ShipCountry": 1,
            "cliente":     1,
            "empleado":    1,
            "detalles":    1,
        }},
    ]

    with ConexionMongo() as mongo:
        resultado = list(mongo.bd["Ordertotal"].aggregate(pipeline))

    if not resultado:
        print(f"\n  Pedido #{order_id} no encontrado en Ordertotal.\n")
        return

    doc = resultado[0]

    print(f"\n  Pedido   : {doc['_id']}")
    print(f"  Fecha    : {doc.get('OrderDate', '—')}")
    shipped  = doc.get('ShippedDate')
    print(f"  Enviado  : {shipped if shipped else 'Sin fecha de envío'}")
    print(f"  Destino  : {doc.get('ShipName')} — "
          f"{doc.get('ShipCity')}, {doc.get('ShipCountry')}")

    cli = doc.get("cliente", {})
    print(f"\n  Cliente  : {cli.get('CompanyName')} ({cli.get('CustomerID')})")
    print(f"             {cli.get('ContactName')} — "
          f"{cli.get('City')}, {cli.get('Country')}")

    emp = doc.get("empleado", {})
    print(f"\n  Atendido : {emp.get('FirstName')} {emp.get('LastName')} "
          f"({emp.get('Title')})")

    detalles = doc.get("detalles", [])
    print(f"\n  {'#':>3}  {'Producto':<35} {'Cat':<15} "
          f"{'P.Unit':>8} {'Cant':>5} {'Desc':>5} {'Subtotal':>10}")
    print(f"  {'-'*3}  {'-'*35} {'-'*15} {'-'*8} {'-'*5} {'-'*5} {'-'*10}")

    total = 0.0
    for i, d in enumerate(detalles, 1):
        precio   = _d128_a_float(d.get("UnitPrice"))
        subtotal = _d128_a_float(d.get("Subtotal"))
        total   += subtotal
        disc_pct = d.get("Discount", 0.0) * 100
        print(f"  {i:>3}  {d.get('ProductName', ''):<35} "
              f"{d.get('CategoryName', ''):<15} "
              f"{precio:>8.2f} {d.get('Quantity', 0):>5} "
              f"{disc_pct:>4.0f}% {subtotal:>10.4f}")

    flete = _d128_a_float(doc.get("Freight"))
    print(f"\n  {'Subtotal pedido':>66}: {total:>10.4f}")
    print(f"  {'Flete':>66}: {flete:>10.2f}")
    print(f"  {'TOTAL':>66}: {total + flete:>10.4f}")
    print()



if __name__ == "__main__":
    try:
        consulta1_categorias_y_productos()
        consulta2_inventario_categoria("Beverages")
        consulta3_factura(10248)
    except (ConnectionError, RuntimeError) as error:
        print("ERROR:", error)