# renfe-bot

[![CI](https://github.com/emartinez-dev/renfe-bot/actions/workflows/ci.yml/badge.svg)](https://github.com/emartinez-dev/renfe-bot/actions/workflows/ci.yml)
[![Python Version](https://img.shields.io/badge/python-%3E%3D%203.12-blue.svg)](https://www.python.org/)
[![Package Manager](https://img.shields.io/badge/package%20manager-uv-purple.svg)](https://github.com/astral-sh/uv)
[![License: MIT](https://img.shields.io/badge/License-MIT-yellow.svg)](https://opensource.org/licenses/MIT)

Bot de Telegram y CLI para monitorizar la disponibilidad de billetes de tren en Renfe y recibir notificaciones push en el móvil en cuanto se libere un asiento.

---

## ⚡ Funcionalidades Principales

- 🤖 **Bot interactivo de Telegram**: Configuración fácil de búsquedas mediante `/buscar`.
- 🔀 **Multi-Tracking Simultáneo**: Monitoriza múltiples trayectos o fechas a la vez en segundo plano.
- 📊 **Panel de Rastreos Activos**: Consulta todos los rastreos en marcha en cualquier momento con `/rastreando`.
- 🗑️ **Cancelación Interactiva Guiada**: Muestra el desglose de rastreos y permite confirmar cuál cancelar por su ID o todos a la vez con `/cancelar`.
- 🔒 **Modo Privado**: Restricción de acceso mediante `ALLOWED_USER_ID` y comando `/id`.
- 🚉 **Búsqueda flexible**: Origen, destino y fechas con validación automática de estaciones y sugerencias.
- 🕒 **Filtros por preguntas Sí/No**: Configuración intuitiva de precio máximo y duración sin tener que poner números cero.
- 💻 **CLI ligero**: Búsquedas rápidas desde la consola (`uv run python src/cli.py`).
- 🐳 **Despliegue 24/7**: Listo para Docker y Docker Compose en segundo plano.

---

## 🚀 Inicio Rápido

### Opción 1: Con Docker Compose (Recomendado para servidores 24/7)

1. Crea tu archivo `.env` a partir de `.env.example`:
   ```bash
   cp .env.example .env
   ```
2. Configura tu token de Telegram y tu ID de usuario opcional:
   ```env
   TELEGRAM_TOKEN=123456789:ABCdefGhIjKlmNopQrsTuvWxYz
   ALLOWED_USER_ID=123456789
   ```
3. Ejecuta el contenedor en segundo plano:
   ```bash
   docker compose up -d --build
   ```

---

### Opción 2: Ejecución local con `uv`

1. Crea el entorno virtual e instala las dependencias con `uv`:
   ```bash
   uv venv
   uv pip install -r requirements.txt
   ```
2. Inicia el bot:
   ```bash
   # En Linux/macOS
   PYTHONPATH=src/ uv run python src/bot.py

   # En Windows PowerShell
   $env:PYTHONPATH="src"; uv run python src/bot.py
   ```
3. Ejecutar los tests:
   ```bash
   uv run pytest
   ```

---

## 📱 Comandos de Telegram

- **/start**: Saludo de bienvenida e inicio del bot.
- **/buscar**: Inicia el cuestionario guiado paso a paso (Origen ➔ Destino ➔ Fecha ➔ Hora mín ➔ Hora máx ➔ Filtros Sí/No).
- **/rastreando**: Muestra el panel con la lista de todos los rastreos activos en curso (`#1`, `#2`, ...).
- **/cancelar**: Despliega la lista interactiva de rastreos para seleccionar cuál cancelar por su ID o cancelar todos.
- **/id**: Muestra tu ID personal de Telegram.
- **/ayuda**: Muestra la lista de comandos disponibles.

---

## 🛠️ Mejoras y Modificaciones en este Fork

Este fork extiende las capacidades del proyecto original con las siguientes mejoras y propósitos:

- 🔀 **Soporte Multi-Tracking Contemporáneo (`TrackerManager`)**: Permite ejecutar múltiples búsquedas simultáneas (diferentes trayectos o diferentes fechas de la misma línea). **Propósito:** Monitorizar varios viajes a la vez de forma desatendida.
- 🗑️ **Menu de cancelación interactiva guiada**: `/cancelar` muestra siempre el desglose del rastreo activo y solicita confirmación del ID a cancelar (incluso con 1 solo rastreo).
- ❓ **Filtros por preguntas Sí/No**: Filtros de precio y duración basados en preguntas afirmativas/negativas limpiadas y validadas sin necesidad de ingresar ceros.
- 🎯 **Filtro de tren específico (Hora mín / Hora máx)**: Flujo directo para acotar la hora de salida (ej. entre 11:30 y 11:35) para rastrear únicamente un tren en concreto.
- 📊 **Comando `/rastreando` e informe inicial de estado**: Muestra el informe inicial con el estado de los trenes encontrados (`Plazas libres` vs `Completo (0 plazas libres)`) y permite consultar las fichas de rastreo activas en cualquier momento.
- 🔒 **Modo Privado y restricción por usuario (`ALLOWED_USER_ID`)**: Restricción de seguridad por ID de Telegram.
- 🔑 **Configuración mediante `.env`**: Carga segura de variables de entorno para Docker Compose.
- ⚡ **Ecosistema basado exclusivamente en `uv`**: Proyecto 100% optimizado para `uv`.

---

## 📄 Licencia

Este proyecto está licenciado bajo los términos de la licencia [MIT](LICENSE).
