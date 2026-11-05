import os
import requests

CLIENT_ID = os.getenv("RINGCENTRAL_CLIENT_ID")
CLIENT_SECRET = os.getenv("RINGCENTRAL_CLIENT_SECRET")
JWT = os.getenv("RINGCENTRAL_JWT")

# Obtener Access Token
response = requests.post(
    "https://platform.ringcentral.com/restapi/oauth/token",
    auth=(CLIENT_ID, CLIENT_SECRET),
    headers={
        "Content-Type": "application/x-www-form-urlencoded"
    },
    data={
        "grant_type": "urn:ietf:params:oauth:grant-type:jwt-bearer",
        "assertion": JWT
    }
)

response.raise_for_status()

access_token = response.json()["access_token"]

print("✅ Access Token obtenido")

# Obtener extensiones
response = requests.get(
    "https://platform.ringcentral.com/restapi/v1.0/account/~/extension",
    headers={
        "Authorization": f"Bearer {access_token}"
    }
)

response.raise_for_status()

extensions = response.json()["records"]

print(f"✅ Extensiones encontradas: {len(extensions)}")

# Crear mapa extensionId -> departamento
dept_map = {}

for ext in extensions:
    ext_id = str(ext["id"])

    depto = ext.get("contact", {}).get(
        "department"
    ) or "Sin departamento"

    dept_map[ext_id] = depto

print(f"✅ Departamentos cargados: {len(dept_map)}")

# Obtener Call Log
response = requests.get(
    "https://platform.ringcentral.com/restapi/v1.0/account/~/call-log?view=Detailed&perPage=1000",
    headers={
        "Authorization": f"Bearer {access_token}"
    }
)

response.raise_for_status()

calls = response.json()["records"]

print(f"✅ Llamadas encontradas: {len(calls)}")

# Mostrar ejemplo de departamentos
print("\nPrimeros 5 departamentos:")

for ext_id, depto in list(dept_map.items())[:5]:
    print(f"{ext_id} -> {depto}")
