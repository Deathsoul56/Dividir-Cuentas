import pandas as pd
import json
import os
from pathlib import Path
import matplotlib.pyplot as plt
import seaborn as sns
from datetime import datetime
from reporte import generar_dashboard_html, convertir_html_a_pdf

# =============================================================================
# CONFIGURACIÓN INICIAL
# =============================================================================

class Config:
    """Clase para centralizar toda la configuración del sistema"""
    
    # Configuración de archivos
    DIRECTORIO_DATA = 'data'
    DIRECTORIO_REPORTES = 'reportes'
    ARCHIVO_EXCEL = 'analisis_gastos.xlsx'
    
    # Configuración de propina
    PROPINA_PORCENTAJE = 10  # Porcentaje de propina
    
    # Configuración de visualización
    COLORES = [
        "#ff9f1c",  # naranja suave
        "#6324b5",  # púrpura base
        "#f24e1e",  # naranja brillante (complementario)
        "#1ecbe1",  # celeste vibrante
        "#f2c94c",  # amarillo dorado
        "#27ae60",  # verde medio
        "#eb5757",  # rojo fuerte
        "#9b51e0",  # lila intenso (parecido al base pero más claro)
        "#2d9cdb",  # azul cielo
        "#6fcf97"  # verde suave
    ]
    
    # Configuración de pandas
    @staticmethod
    def configurar_pandas():
        pd.set_option('display.colheader_justify', 'left')
    
    # Configuración de matplotlib
    @staticmethod
    def configurar_matplotlib():
        sns.set_palette("pastel")
        plt.rcParams['font.size'] = 12


# Aplicar configuraciones iniciales
Config.configurar_pandas()
Config.configurar_matplotlib()


# =============================================================================
# FUNCIONES AUXILIARES
# =============================================================================

def procesar_responsables_csv(valor):
    """
    Procesa la columna de responsables del CSV y la convierte a formato JSON
    
    Args:
        valor: Valor de la columna Responsables del CSV (nombres separados por ';')
    
    Returns:
        String JSON con la lista de responsables
    """
    if pd.isna(valor) or valor == '':
        return '[]'
    # Dividir por punto y coma y eliminar espacios
    responsables_lista = [r.strip() for r in str(valor).split(';')]
    return json.dumps(responsables_lista)


def print_left_aligned(dataframe):
    """
    Función personalizada para mostrar el DataFrame con formato justificado a la izquierda

    Args:
        dataframe: DataFrame a mostrar
    """
    # Determinar el ancho máximo para cada columna usando vectorización
    col_widths = {
        col: max(len(str(col)), dataframe[col].astype(str).str.len().max()) + 2
        for col in dataframe.columns
    }

    # Imprimir encabezados
    header = ""
    for col in dataframe.columns:
        header += str(col).ljust(col_widths[col])
    print(header)
    print("-" * sum(col_widths.values()))

    # Imprimir filas
    for _, row in dataframe.iterrows():
        row_str = ""
        for col in dataframe.columns:
            row_str += str(row[col]).ljust(col_widths[col])
        print(row_str)


def calcular_estadisticas_por_responsable(df, total_cuenta):
    """
    Calcula estadísticas por responsable

    Args:
        df: DataFrame con los datos
        total_cuenta: Total de la cuenta sin propina

    Returns:
        DataFrame con estadísticas por responsable
    """
    # Pre-parsear JSON para evitar múltiples llamadas
    stats = []
    for _, row in df.iterrows():
        resp_list = json.loads(row['Responsables_JSON'])
        if not resp_list:
            continue

        monto_por_persona = row['Total'] / len(resp_list)
        for resp in resp_list:
            stats.append({
                'Responsable': resp,
                'Producto': row['Producto'],
                'Monto_Asignado': monto_por_persona,
                'Monto_con_propina': monto_por_persona * (1 + Config.PROPINA_PORCENTAJE / 100),
                'Personas_Compartiendo': len(resp_list)
            })

    stats_df = pd.DataFrame(stats)

    # Crear resumen por responsable
    resumen = stats_df.groupby('Responsable', as_index=False).agg({
        'Monto_Asignado': 'sum',
        'Monto_con_propina': 'sum',
        'Producto': 'count'
    })

    resumen.columns = ['Responsable', 'Total_Gastado', 'Total_con_Propina', 'Cantidad_Items']
    
    # Calcular porcentajes
    porcentajes = (resumen['Total_Gastado'] / total_cuenta * 100).round(2)
    resumen['Porcentaje_Cuenta'] = porcentajes.apply(lambda x: f"{x}%")

    # Redondear totales
    resumen['Total_Gastado'] = resumen['Total_Gastado'].round().astype(int)
    resumen['Total_con_Propina'] = resumen['Total_con_Propina'].round().astype(int)

    # Ordenar por gasto descendente
    resumen = resumen.sort_values(by='Total_Gastado', ascending=False)

    # Agregar fila de totales
    total_row = pd.DataFrame([{
        'Responsable': 'TOTAL',
        'Total_Gastado': resumen['Total_Gastado'].sum(),
        'Total_con_Propina': resumen['Total_con_Propina'].sum(),
        'Cantidad_Items': resumen['Cantidad_Items'].sum(),
        'Porcentaje_Cuenta': '100%'
    }])

    return pd.concat([resumen, total_row], ignore_index=True)


def generar_tablas_detalle(df, stats_responsables):
    """
    Genera tablas de detalle con productos y precios por responsable

    Args:
        df: DataFrame con los datos
        stats_responsables: DataFrame con estadísticas por responsable

    Returns:
        Tuple de (tabla_productos, tabla_precios)
    """
    # Pre-parsear JSON una sola vez para optimizar
    df_parsed = df.copy()
    df_parsed['Responsables_Parsed'] = df_parsed['Responsables_JSON'].apply(json.loads)
    
    # Determinar items por responsable
    items_por_responsable = {}
    for responsable in stats_responsables[:-1]['Responsable']:
        items = []
        for _, row in df_parsed.iterrows():
            responsables = row['Responsables_Parsed']
            # Contar cuántas veces aparece el responsable en la lista
            cantidad_veces = responsables.count(responsable)
            if cantidad_veces > 0:
                precio_unitario = row['Total'] / len(responsables)
                # Agregar el producto tantas veces como aparezca el responsable
                for _ in range(cantidad_veces):
                    items.append({
                        'producto': row['Producto'],
                        'precio': precio_unitario
                    })
        items_por_responsable[responsable] = items
    
    max_items = max((len(items) for items in items_por_responsable.values()), default=0)

    # Crear columnas dinámicas
    columnas_productos = ['Responsable'] + [f'Item_{i + 1}' for i in range(max_items)]
    columnas_precios = ['Responsable'] + [f'Precio_{i + 1}' for i in range(max_items)] + [
        'Subtotal', f'Propina ({Config.PROPINA_PORCENTAJE}%)', 'Total a Pagar'
    ]

    # Construir filas usando list comprehension (mucho más eficiente)
    filas_productos = []
    filas_precios = []
    
    for responsable, items in items_por_responsable.items():
        fila_productos = {'Responsable': responsable}
        fila_precios = {'Responsable': responsable}
        subtotal = 0

        for i in range(max_items):
            if i < len(items):
                fila_productos[f'Item_{i + 1}'] = items[i]['producto']
                precio = items[i]['precio']
                fila_precios[f'Precio_{i + 1}'] = f"${round(precio)}"
                subtotal += precio
            else:
                fila_productos[f'Item_{i + 1}'] = ''
                fila_precios[f'Precio_{i + 1}'] = ''

        # Calcular totales
        propina_monto = subtotal * (Config.PROPINA_PORCENTAJE / 100)
        total = subtotal + propina_monto
        fila_precios['Subtotal'] = f"${round(subtotal)}"
        fila_precios[f'Propina ({Config.PROPINA_PORCENTAJE}%)'] = f"${round(propina_monto)}"
        fila_precios['Total a Pagar'] = f"${round(total)}"

        filas_productos.append(fila_productos)
        filas_precios.append(fila_precios)

    # Crear DataFrames de una sola vez (mucho más eficiente que concat en loop)
    tabla_productos = pd.DataFrame(filas_productos, columns=columnas_productos)
    tabla_precios = pd.DataFrame(filas_precios, columns=columnas_precios)

    return tabla_productos, tabla_precios


# =============================================================================
# FUNCIONES DE VISUALIZACIÓN
# =============================================================================

def grafico_barras(stats_responsables, palette):
    """
    Genera gráfico de barras de gastos por responsable

    Args:
        stats_responsables: DataFrame con estadísticas por responsable
        palette: Paleta de colores a usar
    """
    plt.figure(figsize=(12, 6))
    
    # Ordenar datos alfabéticamente por responsable
    datos_ordenados = stats_responsables[:-1].sort_values('Responsable', ascending=True)
    
    bar_plot = sns.barplot(
        data=datos_ordenados,
        x='Responsable',
        y='Total_con_Propina',
        hue='Responsable',
        palette=palette,
        legend=False
    )
    plt.title(f'Distribución del Gasto con Propina ({Config.PROPINA_PORCENTAJE}%) por Responsable', fontsize=16)
    plt.xlabel('Responsable', fontsize=12)
    plt.ylabel('Total + Propina ($)', fontsize=12)
    plt.xticks(rotation=45)

    # Formatear valores en las barras
    for p in bar_plot.patches:
        bar_plot.annotate(
            f"${p.get_height():,.0f}",
            (p.get_x() + p.get_width() / 2., p.get_height()),
            ha='center', va='center',
            xytext=(0, 5),
            textcoords='offset points',
            fontsize=10
        )
    plt.tight_layout()
    plt.show()


def grafico_torta(stats_responsables):
    """
    Genera gráfico de torta de distribución de gastos

    Args:
        stats_responsables: DataFrame con estadísticas por responsable
    """
    # Ordenar datos alfabéticamente por responsable
    datos = stats_responsables[:-1].sort_values('Responsable', ascending=True)
    plt.figure(figsize=(10, 10))

    total = datos['Total_con_Propina'].sum()
    wedges, texts, autotexts = plt.pie(
        datos['Total_con_Propina'],
        labels=datos['Responsable'],
        autopct=lambda p: f"${(p / 100) * total:,.0f}\n({p:.1f}%)",
        startangle=90,
        textprops={'fontsize': 12},
        wedgeprops={'edgecolor': 'white', 'linewidth': 1},
        colors=Config.COLORES
    )

    plt.setp(autotexts, size=10, weight="bold")
    plt.setp(texts, size=12)
    plt.title(f'Distribución del Total con Propina ({Config.PROPINA_PORCENTAJE}%)', fontsize=16, pad=20)
    plt.tight_layout()
    plt.show()


def mapa_calor(df, stats_responsables):
    """
    Genera mapa de calor de productos por responsable

    Args:
        df: DataFrame con los datos
        stats_responsables: DataFrame con estadísticas por responsable
    """
    # Pre-parsear JSON y ordenar alfabéticamente
    df_parsed = df.copy()
    df_parsed['Responsables_Parsed'] = df_parsed['Responsables_JSON'].apply(json.loads)
    responsables_unicos = sorted(stats_responsables[:-1]['Responsable'].tolist())
    productos_unicos = df['Producto'].unique()
    
    matriz_valores = pd.DataFrame(0.0, index=productos_unicos, columns=responsables_unicos)

    for _, row in df_parsed.iterrows():
        responsables = row['Responsables_Parsed']
        if not responsables:
            continue
        monto_por_persona = row['Total'] * (1 + Config.PROPINA_PORCENTAJE / 100) / len(responsables)
        # Contar cuántas veces aparece cada responsable
        for resp in responsables_unicos:
            cantidad_veces = responsables.count(resp)
            if cantidad_veces > 0:
                matriz_valores.loc[row['Producto'], resp] += monto_por_persona * cantidad_veces

    # Ordenar por productos más caros
    matriz_valores = matriz_valores.loc[matriz_valores.sum(axis=1).sort_values(ascending=False).index]

    plt.figure(figsize=(12, 8))
    sns.heatmap(
        matriz_valores,
        cmap="YlOrRd",
        annot=False,
        linewidths=.5,
        cbar_kws={'label': 'Valor asignado ($)'}
    )
    plt.title(f'Distribución de Valor (con propina {Config.PROPINA_PORCENTAJE}%) por Producto y Responsable', 
              fontsize=16)
    plt.xlabel('Responsable', fontsize=12)
    plt.ylabel('Producto', fontsize=12)
    plt.xticks(rotation=45)
    plt.yticks(rotation=0)
    plt.tight_layout()
    plt.show()


# =============================================================================
# FUNCIONES DE EXPORTAR A EXCEL
# =============================================================================

def exportar_a_excel(stats_responsables, tabla_productos, tabla_precios, nombre_archivo="resultados.xlsx"):
    """
    Exporta las tablas a un archivo Excel con múltiples hojas

    Args:
        stats_responsables: DataFrame con estadísticas por responsable
        tabla_productos: DataFrame con productos por responsable
        tabla_precios: DataFrame con precios por responsable
        nombre_archivo: Nombre del archivo Excel a generar
    """
    with pd.ExcelWriter(nombre_archivo, engine='xlsxwriter') as writer:
        # Configurar el formato para moneda
        workbook = writer.book
        money_format = workbook.add_format({'num_format': '$#,##0'})

        # Exportar cada DataFrame a una hoja diferente
        stats_responsables.to_excel(writer, sheet_name='Estadísticas', index=False)
        tabla_productos.to_excel(writer, sheet_name='Productos', index=False)
        tabla_precios.to_excel(writer, sheet_name='Precios', index=False)

        # Aplicar formato de moneda a las columnas numéricas
        worksheet = writer.sheets['Estadísticas']
        worksheet.set_column('B:E', 15, money_format)

        worksheet = writer.sheets['Precios']
        # Determinar el rango de columnas de precios (asumiendo que empiezan desde la columna B)
        num_cols = len(tabla_precios.columns)
        worksheet.set_column(1, num_cols - 1, 15)

    print(f"\nArchivo Excel generado: {nombre_archivo}")


# =============================================================================
# FUNCIONES DE CARGA Y PROCESAMIENTO DE DATOS
# =============================================================================

def cargar_y_procesar_csv(archivo_csv):
    """
    Carga y procesa el archivo CSV con los datos de gastos
    
    Args:
        archivo_csv: Nombre del archivo CSV (se buscará en la carpeta 'data')
    
    Returns:
        Tuple de (df_procesado, total_cuenta, total_con_propina)
    """
    # Construir ruta completa desde la carpeta data
    ruta_csv = os.path.join(Config.DIRECTORIO_DATA, archivo_csv)
    
    # Leer CSV
    df_original = pd.read_csv(ruta_csv, decimal=',', thousands='.')
    
    # Extraer totales
    total_cuenta = df_original.loc[df_original['Cant'] == 'Total', 'Total'].values[0]
    total_con_propina = df_original.loc[df_original['Producto'] == 'c/propina', 'Total'].values[0]
    
    # Procesar datos
    df = df_original[:-4].copy()  # Eliminar filas de resumen
    if 'Cant' in df.columns:
        df = df.drop('Cant', axis=1)
    
    # Procesar responsables
    df['Responsables_JSON'] = df['Responsables'].apply(procesar_responsables_csv)
    
    return df, total_cuenta, total_con_propina


def verificar_totales(df, total_cuenta, total_con_propina):
    """
    Verifica que los totales calculados coincidan con los del CSV
    
    Args:
        df: DataFrame procesado
        total_cuenta: Total sin propina del CSV
        total_con_propina: Total con propina del CSV
    """
    suma_productos = df['Total'].sum()
    
    if suma_productos != total_cuenta:
        print(f"⚠️  Diferencia en total: {total_cuenta - suma_productos}")
    
    total_calculado = suma_productos * (1 + Config.PROPINA_PORCENTAJE / 100)
    if abs(total_calculado - total_con_propina) > 0.01:  # Tolerancia para redondeo
        print(f"⚠️  Diferencia en total con propina: {total_con_propina - total_calculado}")


def obtener_configuracion_colores(num_responsables):
    """
    Obtiene la paleta de colores apropiada según el número de responsables
    
    Args:
        num_responsables: Número de responsables únicos
    
    Returns:
        Paleta de colores
    """
    if num_responsables <= len(Config.COLORES):
        return Config.COLORES[:num_responsables]
    return sns.color_palette("husl", num_responsables)


def generar_reportes(stats_responsables, tabla_productos, tabla_precios, 
                     total_cuenta, total_con_propina, nombre_csv):
    """
    Genera todos los reportes (Excel, HTML, PDF)
    
    Args:
        stats_responsables: DataFrame con estadísticas
        tabla_productos: DataFrame con productos
        tabla_precios: DataFrame con precios
        total_cuenta: Total sin propina
        total_con_propina: Total con propina
        nombre_csv: Nombre del archivo CSV (para usar en nombres de archivos)
    """
    # Crear directorio si no existe
    Path(Config.DIRECTORIO_REPORTES).mkdir(exist_ok=True)
    
    fecha_actual = datetime.now().strftime("%Y-%m-%d")
    
    # Extraer nombre base del CSV (sin extensión)
    nombre_base = Path(nombre_csv).stem
    
    # Excel
    exportar_a_excel(stats_responsables, tabla_productos, tabla_precios, Config.ARCHIVO_EXCEL)
    
    # Dashboard HTML
    nombre_dashboard = f"dashboard_{nombre_base}_{fecha_actual}.html"
    ruta_html = generar_dashboard_html(
        stats_responsables, tabla_productos, tabla_precios,
        total_cuenta, total_con_propina, Config.PROPINA_PORCENTAJE, fecha_actual, nombre_dashboard
    )
    
    # PDF desde HTML (ajustado al contenido)
    nombre_pdf = f"dashboard_{nombre_base}_{fecha_actual}.pdf"
    convertir_html_a_pdf(ruta_html, nombre_pdf)


# =============================================================================
# FUNCIÓN PRINCIPAL
# =============================================================================

if __name__ == "__main__":
    """Función principal que ejecuta todo el análisis"""
    
    # Configuración del archivo CSV
    ARCHIVO_CSV = 'Boleta04.csv'
    
    # Cargar y procesar datos
    df, total_cuenta, total_con_propina = cargar_y_procesar_csv(ARCHIVO_CSV)
    
    # Mostrar datos procesados
    print("📊 DataFrame procesado:")
    print_left_aligned(df)
    
    # Verificar totales
    verificar_totales(df, total_cuenta, total_con_propina)
    
    # Estadísticas básicas
    print("\n📈 Estadísticas básicas:")
    print(df.describe())
    
    # Calcular estadísticas por responsable
    print("\n👥 Estadísticas por responsable:")
    stats_responsables = calcular_estadisticas_por_responsable(df, total_cuenta)
    print_left_aligned(stats_responsables)
    
    # Generar gráficos
    num_responsables = len(stats_responsables) - 1  # Sin contar TOTAL
    palette = obtener_configuracion_colores(num_responsables)
    
    grafico_barras(stats_responsables, palette)
    grafico_torta(stats_responsables)
    mapa_calor(df, stats_responsables)
    
    # Generar tablas detalladas
    tabla_productos, tabla_precios = generar_tablas_detalle(df, stats_responsables)
    
    print("\n🛍️  Tabla de Productos por Responsable:")
    print_left_aligned(tabla_productos)
    print("\n💵 Tabla de Precios por Responsable:")
    print_left_aligned(tabla_precios)
    
    # Generar todos los reportes
    generar_reportes(stats_responsables, tabla_productos, tabla_precios, 
                    total_cuenta, total_con_propina, ARCHIVO_CSV)