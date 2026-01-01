import os
import json
from datetime import datetime

# Importar playwright para PDF
try:
    from playwright.sync_api import sync_playwright
    PLAYWRIGHT_DISPONIBLE = True
except ImportError:
    PLAYWRIGHT_DISPONIBLE = False

def generar_datos_json(stats_responsables, tabla_productos, tabla_precios, 
                      total_cuenta, total_con_propina, propina_porcentaje, fecha=None):
    """
    Genera los datos en formato JSON para el frontend React
    
    Args:
        stats_responsables: DataFrame con estadísticas por responsable
        tabla_productos: DataFrame con productos por responsable  
        tabla_precios: DataFrame con precios por responsable
        total_cuenta: Total sin propina
        total_con_propina: Total con propina
        propina_porcentaje: Porcentaje de propina aplicado
        fecha: Fecha del reporte (opcional)
    
    Returns:
        dict: Datos estructurados para React
    """
    
    # Convertir DataFrames a formato JSON amigable usando to_dict para mejor performance
    stats_data = [
        {
            'responsable': row['Responsable'],
            'totalGastado': int(row['Total_Gastado']),
            'totalConPropina': int(row['Total_con_Propina']),
            'cantidadItems': int(row['Cantidad_Items']),
            'porcentajeCuenta': float(str(row['Porcentaje_Cuenta']).replace('%', ''))
        }
        for row in stats_responsables[:-1].to_dict('records')  # Excluir fila TOTAL
    ]
    
    # Preparar productos por responsable (más eficiente con to_dict)
    productos_data = []
    item_cols = [col for col in tabla_productos.columns if col.startswith('Item_')]
    for row in tabla_productos.to_dict('records'):
        productos = [row[col] for col in item_cols if row[col] and row[col] != '']
        if productos:
            productos_data.append({
                'responsable': row['Responsable'],
                'productos': productos
            })
    
    # Estructura final de datos
    data = {
        'resumen': {
            'fecha': fecha or datetime.now().strftime("%Y-%m-%d"),
            'totalSinPropina': int(total_cuenta),
            'totalConPropina': int(total_con_propina),
            'numeroResponsables': len(stats_data),
            'propinaAplicada': propina_porcentaje
        },
        'estadisticas': stats_data,
        'productos': productos_data,
        'totales': {
            'responsable': 'TOTAL',
            'totalGastado': int(stats_responsables.iloc[-1]['Total_Gastado']),
            'totalConPropina': int(stats_responsables.iloc[-1]['Total_con_Propina']),
            'cantidadItems': int(stats_responsables.iloc[-1]['Cantidad_Items'])
        }
    }
    
    return data


def generar_dashboard_html(stats_responsables, tabla_productos, tabla_precios, 
                          total_cuenta, total_con_propina, propina_porcentaje, fecha=None, 
                          nombre_archivo="dashboard_gastos.html"):
    """
    Genera un dashboard HTML con gráficos interactivos usando Chart.js
    
    Args:
        stats_responsables: DataFrame con estadísticas por responsable
        tabla_productos: DataFrame con productos por responsable  
        tabla_precios: DataFrame con precios por responsable
        total_cuenta: Total sin propina
        total_con_propina: Total con propina
        propina_porcentaje: Porcentaje de propina aplicado
        fecha: Fecha del reporte (opcional)
        nombre_archivo: Nombre del archivo HTML a generar
    
    Returns:
        str: Ruta del archivo generado
    """
    
    # Generar datos JSON
    data = generar_datos_json(stats_responsables, tabla_productos, tabla_precios, 
                             total_cuenta, total_con_propina, propina_porcentaje, fecha)
    
    # Crear directorio si no existe
    os.makedirs("reportes", exist_ok=True)
    
    # Formatear los datos para insertar en el HTML
    fecha_reporte = fecha or datetime.now().strftime("%Y-%m-%d")
    
    def format_currency(value):
        # Formatear directamente con separador de miles apropiado
        return f"${int(value):,}".replace(",", ".")
    
    # Crear HTML con datos integrados
    html_content = f'''<!DOCTYPE html>
<html lang="es">
<head>
    <meta charset="UTF-8">
    <meta name="viewport" content="width=device-width, initial-scale=1.0">
    <title>Análisis de Gastos Compartidos</title>
    <script src="https://cdn.jsdelivr.net/npm/chart.js"></script>
    <style>
        * {{ margin: 0; padding: 0; box-sizing: border-box; }}
        body {{ font-family: 'Segoe UI', Tahoma, Geneva, Verdana, sans-serif; background: linear-gradient(135deg, #0f0f23 0%, #1a1a2e 100%); min-height: 100vh; color: #fff; }}
        .app {{ max-width: 1400px; margin: 0 auto; padding: 20px; }}
        .header {{ background: linear-gradient(135deg, #16213e 0%, #0f3460 100%); border-radius: 20px; padding: 30px; margin-bottom: 30px; box-shadow: 0 10px 30px rgba(0,0,0,0.3); text-align: center; border: 1px solid #00d4ff; }}
        .header h1 {{ color: #00d4ff; font-size: 2.5rem; margin-bottom: 15px; font-weight: 700; text-shadow: 0 0 10px rgba(0,212,255,0.3); }}
        .header p {{ color: #a8b2d1; font-size: 1.1rem; }}
        .summary-cards {{ display: grid; grid-template-columns: repeat(auto-fit, minmax(250px, 1fr)); gap: 20px; margin-bottom: 30px; }}
        .card {{ background: linear-gradient(135deg, #16213e 0%, #0f3460 100%); border-radius: 15px; padding: 25px; box-shadow: 0 8px 25px rgba(0,0,0,0.3); transition: transform 0.3s ease, box-shadow 0.3s ease; text-align: center; border: 1px solid #333; }}
        .card:hover {{ transform: translateY(-5px); box-shadow: 0 15px 35px rgba(0,212,255,0.2); border-color: #00d4ff; }}
        .card-icon {{ font-size: 2.5rem; margin-bottom: 15px; }}
        .card-value {{ font-size: 2rem; font-weight: bold; color: #00d4ff; margin-bottom: 5px; text-shadow: 0 0 10px rgba(0,212,255,0.3); }}
        .card-label {{ color: #a8b2d1; font-size: 0.9rem; text-transform: uppercase; letter-spacing: 1px; }}
        .charts-container {{ display: grid; grid-template-columns: 1fr 1fr; gap: 30px; margin-bottom: 30px; }}
        .chart-card {{ background: #000; border-radius: 15px; padding: 25px; box-shadow: 0 8px 25px rgba(0,0,0,0.5); border: 1px solid #333; }}
        .chart-title {{ font-size: 1.3rem; font-weight: 600; color: #00d4ff; margin-bottom: 20px; text-align: center; text-shadow: 0 0 5px rgba(0,212,255,0.3); }}
        .full-width-chart {{ grid-column: 1 / -1; }}
        .chart-container {{ position: relative; height: 400px; width: 100%; }}
        .chart-container.small {{ height: 300px; }}
        .table-container {{ background: linear-gradient(135deg, #16213e 0%, #0f3460 100%); border-radius: 15px; padding: 25px; box-shadow: 0 8px 25px rgba(0,0,0,0.3); overflow-x: auto; margin-bottom: 30px; border: 1px solid #333; }}
        .data-table {{ width: 100%; border-collapse: collapse; margin-top: 15px; }}
        .data-table th, .data-table td {{ padding: 15px 12px; text-align: left; border: 1px solid #454545; }}
        .data-table th {{ background: #000; font-weight: 600; color: #00d4ff; text-transform: uppercase; font-size: 0.95rem; letter-spacing: 1px; }}
        .data-table td {{ background: #1e2328; color: #e8eaed; font-size: 1rem; }}
        .data-table tr:nth-child(even) td {{ background: #2a2d32; }}
        .data-table tr:hover td {{ background: #3a4047 !important; color: #fff !important; }}
        .data-table th:nth-child(3) {{ color: #00ff41; font-size: 1.05rem; text-shadow: 0 0 15px rgba(0,255,65,0.8), 0 0 25px rgba(0,255,65,0.5); }}
        .data-table td:nth-child(3) {{ color: #00ff41 !important; font-weight: bold; font-size: 1.2rem; text-shadow: 0 0 20px rgba(0,255,65,1), 0 0 30px rgba(0,255,65,0.7), 0 0 40px rgba(0,255,65,0.5); }}
        .data-table tr:hover td:nth-child(3) {{ color: #39ff14 !important; text-shadow: 0 0 25px rgba(57,255,20,1), 0 0 35px rgba(57,255,20,0.8); }}
        .total-row {{ background: #00d4ff !important; color: #000 !important; font-weight: bold; }}
        .total-row:hover {{ background: #0099cc !important; }}
        .total-row td {{ background: #00d4ff !important; color: #000 !important; border: 1px solid #0099cc !important; }}
        .total-row td:nth-child(3) {{ color: #5B21B6 !important; font-size: 1.4rem; font-weight: 900; text-shadow: 0 0 25px rgba(91,33,182,1), 0 0 40px rgba(91,33,182,0.8), 0 0 55px rgba(91,33,182,0.6), 0 0 70px rgba(91,33,182,0.4); animation: neonPulse 1.5s ease-in-out infinite; }}
        @keyframes neonPulse {{ 0%, 100% {{ text-shadow: 0 0 25px rgba(91,33,182,1), 0 0 40px rgba(91,33,182,0.8), 0 0 55px rgba(91,33,182,0.6); }} 50% {{ text-shadow: 0 0 35px rgba(91,33,182,1), 0 0 55px rgba(91,33,182,1), 0 0 75px rgba(91,33,182,0.8); }} }}
        .productos-grid {{ display: grid; grid-template-columns: repeat(auto-fit, minmax(300px, 1fr)); gap: 25px; margin-top: 20px; }}
        .producto-card {{ background: linear-gradient(135deg, #1a2540 0%, #16213e 100%); border-radius: 12px; padding: 20px; border: 3px solid #00ff41; box-shadow: 0 8px 20px rgba(0,255,65,0.3), 0 0 40px rgba(0,255,65,0.15); transition: transform 0.3s ease, box-shadow 0.3s ease, border-color 0.3s ease; }}
        .producto-card:hover {{ transform: translateY(-8px) scale(1.02); box-shadow: 0 12px 30px rgba(0,255,65,0.5), 0 0 60px rgba(0,255,65,0.3); border-color: #39ff14; }}
        .producto-card h4 {{ color: #00d4ff; margin-bottom: 15px; font-size: 1.2rem; text-align: center; font-weight: 700; text-shadow: 0 0 10px rgba(0,212,255,0.5); padding: 10px; background: rgba(0,212,255,0.1); border-radius: 8px; border: 1px solid rgba(0,212,255,0.3); }}
        .producto-item {{ background: #0f3460; margin: 5px 0; padding: 8px 12px; border-radius: 5px; font-size: 0.9rem; color: #a8b2d1; display: flex; justify-content: space-between; align-items: center; }}
        .producto-nombre {{ flex: 1; }}
        .producto-precio {{ font-weight: bold; color: #00d4ff; }}
        .totales-card {{ margin-top: 15px; padding-top: 15px; border-top: 2px solid #333; }}
        .total-item {{ background: #1a1a2e; margin: 8px 0; padding: 10px 15px; border-radius: 5px; display: flex; justify-content: space-between; font-weight: 600; }}
        .total-item.final {{ background: #00d4ff; color: #000; font-size: 1.05rem; }}
        @media (max-width: 768px) {{ .charts-container {{ grid-template-columns: 1fr; }} .header h1 {{ font-size: 2rem; }} .summary-cards {{ grid-template-columns: repeat(auto-fit, minmax(200px, 1fr)); }} }}
    </style>
</head>
<body>
    <div class="app">
        <div class="header">
            <h1>📊 Análisis de Gastos Compartidos</h1>
            <p>Reporte generado el {fecha_reporte}</p>
        </div>

        <div class="summary-cards">
            <div class="card">
                <div class="card-icon">💰</div>
                <div class="card-value">{format_currency(data['resumen']['totalSinPropina'])}</div>
                <div class="card-label">Total sin Propina</div>
            </div>
            <div class="card">
                <div class="card-icon">🎯</div>
                <div class="card-value" style="color: #ff9f1c;">{format_currency(data['resumen']['totalConPropina'])}</div>
                <div class="card-label">Total con Propina</div>
            </div>
            <div class="card">
                <div class="card-icon">👥</div>
                <div class="card-value" style="color: #27ae60;">{data['resumen']['numeroResponsables']}</div>
                <div class="card-label">Responsables</div>
            </div>
            <div class="card">
                <div class="card-icon">📈</div>
                <div class="card-value" style="color: #f24e1e;">{data['resumen']['propinaAplicada']}%</div>
                <div class="card-label">Propina Aplicada</div>
            </div>
        </div>

        <div class="charts-container">
            <div class="chart-card">
                <h3 class="chart-title">💰 Gastos por Responsable</h3>
                <div class="chart-container small">
                    <canvas id="barChart"></canvas>
                </div>
            </div>
            
            <div class="chart-card">
                <h3 class="chart-title">🥧 Distribución de Gastos</h3>
                <div class="chart-container small">
                    <canvas id="pieChart"></canvas>
                </div>
            </div>
            
            <div class="chart-card full-width-chart">
                <h3 class="chart-title">📈 Promedio de Gasto por Item</h3>
                <div class="chart-container">
                    <canvas id="lineChart"></canvas>
                </div>
            </div>
        </div>

        <div class="table-container">
            <h3 class="chart-title">📋 Detalle por Responsable</h3>
            <table class="data-table">
                <thead>
                    <tr>
                        <th>Responsable</th>
                        <th>Total Gastado</th>
                        <th>Total c/Propina</th>
                        <th>Cantidad Items</th>
                        <th>% del Total</th>
                        <th>Promedio por Item</th>
                    </tr>
                </thead>
                <tbody>'''
    
    # Agregar filas de la tabla usando join para mejor performance
    filas_tabla = []
    for stat in data['estadisticas']:
        filas_tabla.append(f'''
                    <tr>
                        <td>{stat['responsable']}</td>
                        <td>{format_currency(stat['totalGastado'])}</td>
                        <td>{format_currency(stat['totalConPropina'])}</td>
                        <td>{stat['cantidadItems']}</td>
                        <td>{stat['porcentajeCuenta']:.2f}%</td>
                        <td>{format_currency(stat['totalConPropina'] / stat['cantidadItems'])}</td>
                    </tr>''')
    html_content += ''.join(filas_tabla)
    
    # Agregar fila de totales
    totales = data['totales']
    html_content += f'''
                    <tr class="total-row">
                        <td>TOTAL</td>
                        <td>{format_currency(totales['totalGastado'])}</td>
                        <td>{format_currency(totales['totalConPropina'])}</td>
                        <td>{totales['cantidadItems']}</td>
                        <td>100.00%</td>
                        <td>{format_currency(totales['totalConPropina'] / totales['cantidadItems'])}</td>
                    </tr>
                </tbody>
            </table>
        </div>

        <div class="table-container">
            <h3 class="chart-title">�🛍️ Productos por Responsable</h3>
            <div class="productos-grid">'''
    
    # Convertir a diccionarios para acceso más rápido
    productos_dict = {row['Responsable']: row for row in tabla_productos.to_dict('records')}
    precio_cols = [col for col in tabla_precios.columns if col.startswith('Precio_')]
    
    # Agregar productos con precios usando list para acumular y join al final
    cards_html = []
    for row_precios in tabla_precios.to_dict('records'):
        responsable = row_precios['Responsable']
        producto_row = productos_dict[responsable]
        
        # Construir items
        items_html = []
        for col in precio_cols:
            if row_precios[col] and row_precios[col] != '':
                item_num = col.split('_')[1]
                producto_col = f'Item_{item_num}'
                producto_nombre = producto_row.get(producto_col, '')
                
                if producto_nombre:
                    items_html.append(f'''
                    <div class="producto-item">
                        <span class="producto-nombre">{producto_nombre}</span>
                        <span class="producto-precio">{row_precios[col]}</span>
                    </div>''')
        
        # Construir card completa
        cards_html.append(f'''
                <div class="producto-card">
                    <h4>{responsable}</h4>
                    {''.join(items_html)}
                    <div class="totales-card">
                        <div class="total-item">
                            <span>Subtotal:</span>
                            <span>{row_precios['Subtotal']}</span>
                        </div>
                        <div class="total-item">
                            <span>Propina (10%):</span>
                            <span>{row_precios['Propina (10%)']}</span>
                        </div>
                        <div class="total-item final">
                            <span>Total a Pagar:</span>
                            <span>{row_precios['Total a Pagar']}</span>
                        </div>
                    </div>
                </div>''')
    
    html_content += ''.join(cards_html)
    
    # Continuar con JavaScript
    html_content += f'''
            </div>
        </div>
    </div>

    <script>
        // Datos generados desde Python
        const gastosData = {json.dumps(data, ensure_ascii=False, indent=8)};

        const COLORES = [
            '#00d4ff',  // Celeste brillante
            '#ff6b6b',  // Rojo coral
            '#4ecdc4',  // Turquesa
            '#f9ca24',  // Amarillo oro
            '#6c5ce7',  // Púrpura
            '#26de81',  // Verde esmeralda
            '#fd79a8',  // Rosa chicle
            '#fdcb6e',  // Amarillo suave
            '#a55eea',  // Lila
            '#520325',  // Rojizo oscuro
            '#ff9f43',  // Naranja mandarina
            '#ee5a6f',  // Rojo sandía
            '#0fb9b1',  // Verde azulado
            '#2ed573',  // Verde lima
            '#ffa502',  // Naranja fuerte
            '#ff6348',  // Rojo salmón
            '#747d8c',  // Gris azulado
            '#5f27cd',  // Púrpura oscuro
            '#00d2d3',  // Cian
            '#ff9ff3'   // Rosa lavanda
        ];

        function formatCurrency(value) {{
            return new Intl.NumberFormat('es-CL', {{
                style: 'currency',
                currency: 'CLP'
            }}).format(value);
        }}

        function crearGraficoBarras(data) {{
            const ctx = document.getElementById('barChart').getContext('2d');
            new Chart(ctx, {{
                type: 'bar',
                data: {{
                    labels: data.estadisticas.map(item => item.responsable),
                    datasets: [{{
                        label: 'Total con Propina',
                        data: data.estadisticas.map(item => item.totalConPropina),
                        backgroundColor: COLORES,
                        borderColor: COLORES.map(color => color + 'AA'),
                        borderWidth: 2,
                        borderRadius: 8,
                        borderSkipped: false,
                    }}]
                }},
                options: {{
                    responsive: true,
                    maintainAspectRatio: false,
                    plugins: {{
                        legend: {{ display: false }},
                        tooltip: {{
                            backgroundColor: 'rgba(0, 0, 0, 0.8)',
                            titleColor: '#00d4ff',
                            bodyColor: '#fff',
                            borderColor: '#00d4ff',
                            borderWidth: 1,
                            callbacks: {{
                                label: function(context) {{
                                    return formatCurrency(context.parsed.y);
                                }}
                            }}
                        }}
                    }},
                    scales: {{
                        x: {{
                            ticks: {{
                                color: '#a8b2d1'
                            }},
                            grid: {{
                                color: '#333'
                            }}
                        }},
                        y: {{
                            beginAtZero: true,
                            ticks: {{
                                color: '#a8b2d1',
                                callback: function(value) {{
                                    return formatCurrency(value);
                                }}
                            }},
                            grid: {{
                                color: '#333'
                            }}
                        }}
                    }}
                }}
            }});
        }}

        function crearGraficoTorta(data) {{
            const ctx = document.getElementById('pieChart').getContext('2d');
            new Chart(ctx, {{
                type: 'doughnut',
                data: {{
                    labels: data.estadisticas.map(item => item.responsable),
                    datasets: [{{
                        data: data.estadisticas.map(item => item.totalConPropina),
                        backgroundColor: COLORES,
                        borderColor: '#000',
                        borderWidth: 2,
                        hoverOffset: 10
                    }}]
                }},
                options: {{
                    responsive: true,
                    maintainAspectRatio: false,
                    plugins: {{
                        legend: {{
                            position: 'bottom',
                            labels: {{
                                padding: 20,
                                usePointStyle: true,
                                font: {{ size: 12 }},
                                color: '#a8b2d1'
                            }}
                        }},
                        tooltip: {{
                            backgroundColor: 'rgba(0, 0, 0, 0.8)',
                            titleColor: '#00d4ff',
                            bodyColor: '#fff',
                            borderColor: '#00d4ff',
                            borderWidth: 1,
                            callbacks: {{
                                label: function(context) {{
                                    const label = context.label || '';
                                    const value = formatCurrency(context.parsed);
                                    const total = context.dataset.data.reduce((sum, val) => sum + val, 0);
                                    const percentage = ((context.parsed / total) * 100).toFixed(1);
                                    return `${{label}}: ${{value}} (${{percentage}}%)`;
                                }}
                            }}
                        }}
                    }}
                }}
            }});
        }}


        function crearGraficoLineas(data) {{
            const ctx = document.getElementById('lineChart').getContext('2d');
            // Calcular y ordenar promedios
            const promedios = data.estadisticas
                .map(item => ({{
                    responsable: item.responsable,
                    promedio: item.totalConPropina / item.cantidadItems
                }}))
                .sort((a, b) => a.promedio - b.promedio);

            new Chart(ctx, {{
                type: 'line',
                data: {{
                    labels: promedios.map(item => item.responsable),
                    datasets: [{{
                        label: 'Promedio por Item',
                        data: promedios.map(item => item.promedio),
                        borderColor: '#4ecdc4',
                        backgroundColor: 'rgba(78, 205, 196, 0.1)',
                        borderWidth: 3,
                        pointBackgroundColor: '#4ecdc4',
                        pointBorderColor: '#000',
                        pointBorderWidth: 2,
                        pointRadius: 8,
                        pointHoverRadius: 12,
                        fill: true,
                        tension: 0.4
                    }}]
                }},
                options: {{
                    responsive: true,
                    maintainAspectRatio: false,
                    plugins: {{
                        legend: {{ display: false }},
                        tooltip: {{
                            backgroundColor: 'rgba(0, 0, 0, 0.8)',
                            titleColor: '#00d4ff',
                            bodyColor: '#fff',
                            borderColor: '#00d4ff',
                            borderWidth: 1,
                            callbacks: {{
                                label: function(context) {{
                                    return `Promedio: ${{formatCurrency(context.parsed.y)}}`;
                                }}
                            }}
                        }}
                    }},
                    scales: {{
                        x: {{
                            ticks: {{
                                color: '#a8b2d1'
                            }},
                            grid: {{
                                color: '#333'
                            }}
                        }},
                        y: {{
                            beginAtZero: true,
                            ticks: {{
                                color: '#a8b2d1',
                                callback: function(value) {{
                                    return formatCurrency(value);
                                }}
                            }},
                            grid: {{
                                color: '#333'
                            }}
                        }}
                    }}
                }}
            }});
        }}

        // Inicializar la aplicación
        function inicializarApp() {{
            crearGraficoBarras(gastosData);
            crearGraficoTorta(gastosData);
            crearGraficoLineas(gastosData);
        }}

        // Esperar a que se cargue la página
        document.addEventListener('DOMContentLoaded', function() {{
            setTimeout(inicializarApp, 100);
        }});
    </script>
</body>
</html>'''
    
    # Guardar archivo
    ruta_archivo = os.path.join("reportes", nombre_archivo)
    with open(ruta_archivo, 'w', encoding='utf-8') as f:
        f.write(html_content)
    
    print(f"\n✅ Dashboard HTML generado: {ruta_archivo}")
    return ruta_archivo


def convertir_html_a_pdf(ruta_html, nombre_pdf="dashboard_gastos.pdf"):
    """
    Convierte un archivo HTML a PDF ajustándose al contenido sin bordes blancos.
    Replica el comportamiento de "guardar como PDF" del navegador en una sola página.
    
    Args:
        ruta_html: Ruta del archivo HTML a convertir
        nombre_pdf: Nombre del archivo PDF de salida
    
    Returns:
        str: Ruta del archivo PDF generado o None si hay error
    """
    
    if not PLAYWRIGHT_DISPONIBLE:
        print("❌ Playwright no está instalado. Instala con:")
        print("   pip install playwright")
        print("   playwright install chromium")
        return None
    
    try:
        print("\n📸 Generando PDF desde HTML...")
        
        with sync_playwright() as p:
            browser = p.chromium.launch()
            page = browser.new_page()
            
            # Cargar el archivo HTML
            ruta_completa = os.path.abspath(ruta_html)
            page.goto(f"file:///{ruta_completa}")
            
            # Esperar a que se carguen los gráficos de Chart.js
            page.wait_for_timeout(2000)
            
            # Obtener dimensiones del contenido
            dimensiones = page.evaluate("""
                () => {
                    const body = document.body;
                    const html = document.documentElement;
                    const height = Math.max(
                        body.scrollHeight,
                        body.offsetHeight,
                        html.clientHeight,
                        html.scrollHeight,
                        html.offsetHeight
                    );
                    const width = Math.max(
                        body.scrollWidth,
                        body.offsetWidth,
                        html.clientWidth,
                        html.scrollWidth,
                        html.offsetWidth
                    );
                    return { width, height };
                }
            """)
            
            # Generar PDF ajustado al contenido sin márgenes
            ruta_pdf = os.path.join("reportes", nombre_pdf)
            page.pdf(
                path=ruta_pdf,
                width=f"{dimensiones['width']}px",
                height=f"{dimensiones['height']}px",
                print_background=True,
                margin={'top': '0', 'bottom': '0', 'left': '0', 'right': '0'}
            )
            
            browser.close()
        
        print(f"✅ PDF generado: {ruta_pdf}")
        return ruta_pdf
        
    except Exception as e:
        print(f"❌ Error al generar PDF: {str(e)}")
        return None
