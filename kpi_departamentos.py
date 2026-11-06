import os
import requests

from datetime import datetime, timedelta
from zoneinfo import ZoneInfo
from collections import defaultdict

CLIENT_ID = os.getenv("RINGCENTRAL_CLIENT_ID")
CLIENT_SECRET = os.getenv("RINGCENTRAL_CLIENT_SECRET")
JWT = os.getenv("RINGCENTRAL_JWT")
CHAT_ID = os.getenv("RINGCENTRAL_CHAT_ID")

SMS_FROM = os.getenv("RINGCENTRAL_SMS_FROM")
SMS_TO = os.getenv("RINGCENTRAL_SMS_TO")

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

# Calcular ayer en horario CDMX
tz = ZoneInfo("America/Mexico_City")

hoy = datetime.now(tz)

ayer_inicio = (
    hoy - timedelta(days=1)
).replace(
    hour=0,
    minute=0,
    second=0,
    microsecond=0
)

ayer_fin = ayer_inicio + timedelta(days=1)

date_from = ayer_inicio.isoformat()
date_to = ayer_fin.isoformat()

print(f"📅 Consultando desde: {date_from}")
print(f"📅 Consultando hasta: {date_to}")

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

# Crear mapa ExtensionId -> Departamento o Nombre
dept_map = {}

for ext in extensions:

    ext_id = str(ext["id"])

    depto = (
        ext.get("contact", {}).get("department")
        or f"[{ext.get('type')}] {ext.get('name')}"
    )

    dept_map[ext_id] = depto

print(f"✅ Departamentos cargados: {len(dept_map)}")

# Obtener Call Log
calls = []
page = 1

while True:

    response = requests.get(
        "https://platform.ringcentral.com/restapi/v1.0/account/~/call-log",
        headers={
            "Authorization": f"Bearer {access_token}"
        },
        params={
            "view": "Detailed",
            "dateFrom": date_from,
            "dateTo": date_to,
            "perPage": 1000,
            "page": page
        }
    )

    response.raise_for_status()

    data = response.json()

    registros = data.get("records", [])

    calls.extend(registros)

    print(f"📞 Página {page}: {len(registros)} llamadas")

    if len(registros) < 1000:
        break

    page += 1

print(f"✅ Total llamadas encontradas: {len(calls)}")

# KPI por departamento
stats = defaultdict(lambda: {
    "total": 0,
    "connected": 0,
    "busy": 0,
    "no_answer": 0,
    "hang_up": 0,
    "wrong_number": 0,
    "call_failed": 0
})

for call in calls:

    ext_id = call.get("from", {}).get("extensionId")

    if not ext_id:
        continue

    depto = dept_map.get(
        str(ext_id),
        "Sin departamento"
    )

    resultado = call.get("result", "")

    stats[depto]["total"] += 1

    if resultado == "Call connected":
        stats[depto]["connected"] += 1

    elif resultado == "Busy":
        stats[depto]["busy"] += 1

    elif resultado == "No Answer":
        stats[depto]["no_answer"] += 1

    elif resultado == "Hang Up":
        stats[depto]["hang_up"] += 1

    elif resultado == "Wrong Number":
        stats[depto]["wrong_number"] += 1

    elif resultado in [
        "Call Failed",
        "Call Failure"
    ]:
        stats[depto]["call_failed"] += 1

# Crear mensaje
mensaje = "📊 KPI RINGCENTRAL - AYER\n\n"
mensaje += f"📅 Desde: {date_from}\n"
mensaje += f"📅 Hasta: {date_to}\n\n"

print("\n📊 KPI POR DEPARTAMENTO\n")

for depto, valores in sorted(
    stats.items(),
    key=lambda x: x[1]["total"],
    reverse=True
):

    total = valores["total"]
    connected = valores["connected"]

    efectividad = (
        connected / total * 100
        if total > 0 else 0
    )

    print(f"\n{depto}")
    print(f"Total llamadas: {total}")
    print(f"✅ Connected: {valores['connected']}")
    print(f"📞 Busy: {valores['busy']}")
    print(f"⏳ No Answer: {valores['no_answer']}")
    print(f"☎️ Hang Up: {valores['hang_up']}")
    print(f"❌ Wrong Number: {valores['wrong_number']}")
    print(f"🚨 Call Failed: {valores['call_failed']}")
    print(f"🎯 Efectividad: {efectividad:.1f}%")

    mensaje += (
        f"🏢 {depto}\n"
        f"Total llamadas: {total}\n"
        f"✅ Connected: {valores['connected']}\n"
        f"📞 Busy: {valores['busy']}\n"
        f"⏳ No Answer: {valores['no_answer']}\n"
        f"☎️ Hang Up: {valores['hang_up']}\n"
        f"❌ Wrong Number: {valores['wrong_number']}\n"
        f"🚨 Call Failed: {valores['call_failed']}\n"
        f"🎯 Efectividad: {efectividad:.1f}%\n\n"
    )

print(mensaje)

# Enviar a Chat RingCentral
response = requests.post(
    f"https://platform.ringcentral.com/restapi/v1.0/glip/chats/{CHAT_ID}/posts",
    headers={
        "Authorization": f"Bearer {access_token}",
        "Content-Type": "application/json"
    },
    json={
        "text": mensaje
    }
)

response.raise_for_status()

print("✅ KPI enviado a RingCentral Chat")

# KPI GLOBAL PARA SMS
global_total = 0
global_connected = 0
global_busy = 0
global_no_answer = 0
global_hang_up = 0
global_wrong_number = 0
global_call_failed = 0

for valores in stats.values():
    global_total += valores["total"]
    global_connected += valores["connected"]
    global_busy += valores["busy"]
    global_no_answer += valores["no_answer"]
    global_hang_up += valores["hang_up"]
    global_wrong_number += valores["wrong_number"]
    global_call_failed += valores["call_failed"]

efectividad_global = (
    global_connected / global_total * 100
    if global_total > 0 else 0
)

sms_text = (
    f"KPI AYER OTP\n"
    f"Total:{global_total}\n"
    f"Conn:{global_connected}\n"
    f"Busy:{global_busy}\n"
    f"NoAns:{global_no_answer}\n"
    f"HangUp:{global_hang_up}\n"
    f"Wrong:{global_wrong_number}\n"
    f"Failed:{global_call_failed}\n"
    f"Efec:{efectividad_global:.1f}%"
)

for numero in SMS_TO.split(","):

    response = requests.post(
        "https://platform.ringcentral.com/restapi/v1.0/account/~/extension/~/sms",
        headers={
            "Authorization": f"Bearer {access_token}",
            "Content-Type": "application/json"
        },
        json={
            "from": {
                "phoneNumber": SMS_FROM
            },
            "to": [
                {
                    "phoneNumber": numero.strip()
                }
            ],
            "text": sms_text
        }
    )

    print(f"SMS para {numero}: {response.status_code}")
    print(response.text)

    response.raise_for_status()

print("✅ Todos los SMS enviados")
