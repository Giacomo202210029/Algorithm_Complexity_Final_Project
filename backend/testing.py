import pandas as pd

# Cargar los datos
edges = pd.read_csv('edges.csv', header=None, names=['id', 'x', 'y'])

# Reemplazar los valores nulos con un valor por defecto
# Puedes cambiar este valor por el que consideres más apropiado
edges = edges.fillna(0)

# Guardar los datos limpios
edges.to_csv('edges.csv', index=False, header=False)