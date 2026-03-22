import svgwrite
import math

try:
    from PIL import ImageFont
    PILLOW_AVAILABLE = True
except ImportError:
    PILLOW_AVAILABLE = False


# --- Medición de ancho de carácter ---

def cargar_fuente_pillow(font_path, font_size):
    """Intenta cargar una fuente TTF con Pillow para medir anchos reales."""
    try:
        return ImageFont.truetype(font_path, font_size)
    except Exception:
        return None


def ancho_char(char, font_size, fuente_pillow=None):
    """
    Calcula el ancho de un carácter.
    - Si hay una fuente Pillow cargada, usa métricas reales.
    - Si no, usa aproximaciones mejoradas por categoría tipográfica.
    """
    if fuente_pillow is not None:
        try:
            bbox = fuente_pillow.getbbox(char)
            if bbox:
                return bbox[2] - bbox[0]
        except Exception:
            pass

    # Fallback: aproximaciones por categoría tipográfica
    if char == ' ':
        return font_size * 0.30
    elif char in 'iIl1|.:,;!':
        return font_size * 0.28
    elif char in 'fjtr':
        return font_size * 0.38
    elif char in 'abcdeghknopqsuvxyz':
        return font_size * 0.55
    elif char in 'ABCDEFGHIJKLMNOPQRSTUVWXYZ':
        return font_size * 0.65
    elif char in 'mwMW':
        return font_size * 0.80
    elif char in '()[]{}-_/\\':
        return font_size * 0.40
    elif char in '0123456789':
        return font_size * 0.55
    else:
        return font_size * 0.55


def ancho_palabra(palabra, font_size, fuente_pillow=None):
    if fuente_pillow is not None:
        try:
            bbox = fuente_pillow.getbbox(palabra)
            if bbox:
                return bbox[2] - bbox[0]
        except Exception:
            pass
    return sum(ancho_char(c, font_size, fuente_pillow) for c in palabra)


# --- Distribución en anillos ---

def distribuir_palabras_anillos(palabras, font_size, radio_inicial, incremento_radio, fuente_pillow=None):
    """Distribuye palabras en anillos concéntricos según la circunferencia de cada uno."""
    anillos = []
    current_radius = radio_inicial
    current_anillo = []
    longitud_actual = 0
    espacio = ancho_char(' ', font_size, fuente_pillow)

    for palabra in palabras:
        palabra_long = ancho_palabra(palabra, font_size, fuente_pillow)
        needed = palabra_long + (espacio if current_anillo else 0)

        if longitud_actual + needed > 2 * math.pi * current_radius:
            if current_anillo:
                anillos.append((current_radius, current_anillo))
            current_radius += incremento_radio
            current_anillo = [palabra]
            longitud_actual = palabra_long
        else:
            current_anillo.append(palabra)
            longitud_actual += needed

    if current_anillo:
        anillos.append((current_radius, current_anillo))

    return anillos


# --- Generación del SVG ---

def generar_vinilo_svg(
    texto,
    font_size=16,
    radio_inicial=100,
    incremento_radio=40,
    font_name="CourierPrime-Regular",
    google_fonts_url=None,
    font_path=None,
    output_file="svg/vinilo.svg",
    canvas_ancho=1587,         # Ancho en px — A3 a 96ppp
    canvas_alto=2245,          # Alto en px  — A2 a 96ppp
    margen_superior=200,       # Espacio reservado arriba (título, fecha...)
    margen_inferior=350,       # Espacio reservado abajo (canción, artista...)
    reserva_centro=80,         # Radio libre en el centro para la etiqueta del vinilo
    radio_disco=None,          # Radio del círculo negro (por defecto: radio_inicial - 10)
    radio_etiqueta=None,       # Radio de la etiqueta de color (por defecto: reserva_centro * 0.75)
    color_etiqueta="#ff0000",  # Color de la etiqueta central
    hueco_aguja_grados=15      # Grados libres reservados para la aguja del tocadiscos
):
    import os
    os.makedirs(os.path.dirname(output_file), exist_ok=True)
    dwg = svgwrite.Drawing(output_file, profile='full',
                           size=(canvas_ancho, canvas_alto))

    # Centro horizontal: mitad del ancho
    # Centro vertical: mitad del área útil (entre márgenes)
    center_x = canvas_ancho / 2
    area_util = canvas_alto - margen_superior - margen_inferior
    center_y = margen_superior + area_util / 2

    # Radios por defecto
    if radio_disco is None:
        radio_disco = radio_inicial - 10
    if radio_etiqueta is None:
        radio_etiqueta = reserva_centro * 0.75

    # --- Fondo blanco ---
    dwg.add(dwg.rect(insert=(0, 0), size=(canvas_ancho, canvas_alto), fill="white"))

    # Importar Google Fonts si se indica
    if google_fonts_url:
        style = f"@import url('{google_fonts_url}');"
        dwg.defs.add(dwg.style(style))

    # --- Disco negro ---
    dwg.add(dwg.circle(center=(center_x, center_y), r=radio_disco, fill="#111111"))

    # --- Etiqueta central de color ---
    dwg.add(dwg.circle(center=(center_x, center_y), r=radio_etiqueta, fill=color_etiqueta))

    # --- Agujero central del vinilo ---
    dwg.add(dwg.circle(center=(center_x, center_y), r=max(3, radio_etiqueta * 0.06), fill="#111111"))

    # Cargar fuente Pillow para métricas reales (opcional)
    fuente_pillow = None
    if font_path and PILLOW_AVAILABLE:
        fuente_pillow = cargar_fuente_pillow(font_path, font_size)
        if fuente_pillow:
            print(f"✅ Fuente '{font_path}' cargada para métricas reales.")
        else:
            print(f"⚠️  No se pudo cargar '{font_path}'. Usando aproximaciones.")
    elif not PILLOW_AVAILABLE and font_path:
        print("⚠️  Pillow no está instalado. Usando aproximaciones de ancho.")

    palabras = texto.split()
    anillos = distribuir_palabras_anillos(
        palabras, font_size, radio_inicial, incremento_radio, fuente_pillow
    )

    # Ángulo inicial: -45 grados (arriba a la derecha)
    angulo_inicio = math.radians(-45)

    # Zona de exclusión para la aguja del tocadiscos: arco reservado centrado en angulo_inicio
    # hueco_aguja define cuántos grados quedan libres alrededor del punto de inicio
    hueco_aguja = math.radians(hueco_aguja_grados)
    angulo_dibujo_inicio = angulo_inicio + hueco_aguja / 2
    angulo_dibujo_fin    = angulo_inicio + 2 * math.pi - hueco_aguja / 2
    arco_disponible      = angulo_dibujo_fin - angulo_dibujo_inicio  # siempre < 2π

    for radius, anillo_palabras in anillos:
        # No dibujar dentro del área reservada para la etiqueta central
        if radius < reserva_centro:
            continue

        longitud_texto = sum(ancho_palabra(p, font_size, fuente_pillow) for p in anillo_palabras)
        espacio = ancho_char(' ', font_size, fuente_pillow)
        n = len(anillo_palabras)
        longitud_con_espacios = longitud_texto + espacio * n
        arco_disponible_px = arco_disponible * radius

        # Espacio extra repartido entre las n separaciones dentro del arco disponible
        espacio_extra = (arco_disponible_px - longitud_con_espacios) / max(1, n)

        current_angle = angulo_dibujo_inicio

        for i, palabra in enumerate(anillo_palabras):
            for char in palabra:
                theta = current_angle
                x = center_x + radius * math.cos(theta)
                y = center_y + radius * math.sin(theta)
                rotation = math.degrees(theta) + 90

                dwg.add(dwg.text(
                    char,
                    insert=(x, y),
                    transform=f"rotate({rotation},{x},{y})",
                    font_size=font_size,
                    font_family=font_name
                ))

                current_angle += ancho_char(char, font_size, fuente_pillow) / radius

            # Espacio tras cada palabra, incluida la última
            current_angle += (espacio + espacio_extra) / radius

    dwg.save()
    print(f"✅ SVG generado: {output_file}")


# --- Entrada interactiva ---

if __name__ == "__main__":
    print("Pega toda la letra de la canción. Escribe 'FIN' en una línea nueva para terminar:")
    lineas = []
    while True:
        linea = input()
        if linea.strip().upper() == 'FIN':
            break
        lineas.append(linea)
    texto_completo = " ".join(lineas)

    generar_vinilo_svg(
        texto_completo,
        font_size=20,
        radio_inicial=125,
        incremento_radio=40,
        font_name="CourierPrime-Regular",
        font_path="fonts/CourierPrime-Regular.ttf",
        canvas_ancho=1587,
        canvas_alto=2245,
        margen_superior=200,
        margen_inferior=350,
        color_etiqueta="#ff0000",
    )