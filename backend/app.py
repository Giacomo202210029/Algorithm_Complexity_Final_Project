from flask import Flask, request, jsonify, send_file
import pandas as pd
import networkx as nx
import matplotlib

matplotlib.use('Agg')
import matplotlib.pyplot as plt
from matplotlib.offsetbox import OffsetImage, AnnotationBbox
from flask_cors import CORS
import os
import time

app = Flask(__name__)
CORS(app)


X = 100  # Múltiplo para casas
Z = 150  # Múltiplo para pizzerías


consumo_por_100_km = 3.5
precio_gasolina_por_litro = 1.60  # Precio de la gasolina en euros por litro


try:
    nodes = pd.read_csv('nodes.csv', header=None, names=['id', 'x', 'y'], sep=' ',
                        dtype={'id': int, 'x': float, 'y': float})
    edges = pd.read_csv('edges.csv', header=None, names=['id', 'source', 'target', 'weight'], sep=' ',
                        dtype={'id': int, 'source': int, 'target': int, 'weight': float})
    print("Nodes and edges loaded successfully")
except Exception as e:
    print(f"Error loading CSV files: {e}")
    raise

# Verificar datos
if nodes.isnull().values.any():
    raise ValueError("El archivo nodes.csv contiene valores nulos (NaN). Verifica tu archivo de datos.")
if edges.isnull().values.any():
    raise ValueError("El archivo edges.csv contiene valores nulos (NaN). Verifica tu archivo de datos.")

# Crear grafo
try:
    G = nx.from_pandas_edgelist(edges, 'source', 'target', edge_attr='weight')
    pos = {int(row['id']): (row['x'], row['y']) for idx, row in nodes.iterrows()}
    nx.set_node_attributes(G, pos, 'pos')
    print(f"Graph created successfully with {len(G.nodes)} nodes and {len(G.edges)} edges")
except Exception as e:
    print(f"Error creating graph: {e}")
    raise



def add_images(ax, pos, image_path, node_list, zoom=0.1):
    for n in node_list:
        img = plt.imread(image_path)
        imagebox = OffsetImage(img, zoom=zoom)
        ab = AnnotationBbox(imagebox, pos[n], frameon=False)
        ax.add_artist(ab)


@app.route('/')
def home():
    return "Bienvenido al servidor Flask. Usa /graph para ver el grafo o /shortest_path para encontrar el camino más corto."


@app.route('/shortest_path', methods=['POST'])
def shortest_path():
    try:
        data = request.json
        target = int(float(data.get('target')))

        if target not in G:
            return jsonify({'error': f'Node {target} not found in graph'}), 404

        # Filtrar los nodos que son pizzerías
        pizzeria_nodes = [n for n in G.nodes if n % Z == 0 and n % X != 0]

        if not pizzeria_nodes:
            return jsonify({'error': 'No pizzerias found in graph'}), 404

        # Calcular la distancia mínima desde el nodo de destino a cualquier pizzería
        shortest_path_length = float('inf')
        shortest_path = None
        closest_pizzeria = None

        for pizzeria in pizzeria_nodes:
            try:
                path = nx.shortest_path(G, source=pizzeria, target=target, weight='weight')
                distance = nx.shortest_path_length(G, source=pizzeria, target=target, weight='weight')
                if distance < shortest_path_length:
                    shortest_path_length = distance
                    shortest_path = path
                    closest_pizzeria = pizzeria
            except nx.NetworkXNoPath:
                continue

        if shortest_path is None:
            return jsonify({'error': 'No path found to any pizzeria'}), 404

        distance_km = shortest_path_length / 1000.0
        average_speed_kmh = 35.0
        estimated_time_hours = distance_km / average_speed_kmh
        estimated_time_minutes = round(estimated_time_hours * 60)

        # Cálculo del costo de la gasolina
        consumo_gasolina = (distance_km / 100) * consumo_por_100_km
        costo_gasolina = round(consumo_gasolina * precio_gasolina_por_litro, 2)

        with open('shortest_path.txt', 'w') as f:
            for node in shortest_path:
                f.write(f"{int(node)}\n")

        return jsonify({
            'path': shortest_path,
            'distance': shortest_path_length,
            'distance_km': distance_km,
            'estimated_time_minutes': estimated_time_minutes,
            'average_speed_kmh': average_speed_kmh,
            'costo_gasolina': costo_gasolina
        })
    except nx.NetworkXNoPath:
        return jsonify({'error': 'No path found'}, 404)
    except nx.NodeNotFound:
        return jsonify({'error': 'Node not found in graph'}, 404)
    except Exception as ex:
        print(f"Unexpected error in shortest_path: {ex}")
        return jsonify({'error': str(ex)}), 500


@app.route('/graph', methods=['GET'])
def graph():
    try:
        image_id = request.args.get('imageId', default='0', type=int)
        if os.path.exists('static/graph' + str(image_id) + '.png'):
            os.remove('static/graph' + str(image_id) + '.png')

        fig, ax = plt.subplots(figsize=(15, 15))  # Ajustar el tamaño de la figura para un mejor ajuste en pantalla


        nx.draw(G, pos, with_labels=False, node_size=50, font_size=10, node_color='lightblue', edge_color='gray',
                ax=ax)


        path = []
        if os.path.exists('shortest_path.txt'):
            with open('shortest_path.txt', 'r') as f:
                path = [int(float(line.strip())) for line in f]

            shortest_path_edges = [(path[i], path[i + 1]) for i in range(len(path) - 1)]


            nx.draw_networkx_nodes(G, pos, nodelist=path, node_color='red', node_size=100,
                                   ax=ax)


            nx.draw_networkx_edges(G, pos, edgelist=shortest_path_edges, edge_color='red', width=2,
                                   ax=ax)  # Ajustar el ancho de las aristas en el camino más corto


        pizzeria_nodes = [n for n in G.nodes if n % Z == 0 and n % X != 0]

        # Agregar iconos
        add_images(ax, pos, 'static/icons/pizzeria.png', pizzeria_nodes, zoom=0.05)


        if path:
            target_node = path[-1]
            add_images(ax, pos, 'static/icons/house.png', [target_node], zoom=0.05)  # Ajustar el tamaño del icono

        # Asegurarse de que el directorio 'static' existe
        os.makedirs('static', exist_ok=True)

        # Guardar la imagen del grafo
        plt.savefig('static/graph' + str(image_id) + '.png')
        plt.close()
        print("Graph image saved successfully.")

        time.sleep(0.5)

        if not os.path.exists('static/graph' + str(image_id) + '.png'):
            raise FileNotFoundError("The graph image was not saved correctly.")

        return send_file('static/graph' + str(image_id) + '.png', mimetype='image/png')
    except Exception as ex:
        print(f"Error generating graph image: {ex}")
        return jsonify({"error": str(ex)}), 500


if __name__ == '__main__':
    app.run(debug=True)
