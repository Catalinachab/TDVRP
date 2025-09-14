import json, math, argparse, csv
from build_pwl_arc import *

def pwl_f(t:float, i:int, j:int, instance_name:str) -> tuple:
   '''
   devuelve (t, y) donde y es el tiempo de viaje en el arco (i,j) si se sale en t
   '''
   # ver entre que 2 bkpts esta t
   # calcular la pendiente = (y2-y1)/(x2-x1)
   # para ver que y corresponde a t en (t, y) de la pwl de time ...?
   instance_path = "data/instancias-dabia_et_al_2013/" + instance_name + ".json"
   I = json.load(open(instance_path))
   D = I["distances"][i][j]
   cid = I["clusters"][i][j]
   VZ = I["cluster_speeds"][cid]
   Zs = Z(I); per = P(I)
   pts = tau_pts(D, VZ, Zs, per)
   for i in range(len(pts)-1):
      if t >= pts[i][0] and t <= pts[i+1][0]:
         m = (pts[i+1][1] - pts[i][1])/(pts[i+1][0] - pts[i][0]) #pendiente
         ord_origen = pts[i][1] - (m * pts[i][0]) #ordenada al origen
         y = m * t + ord_origen
         return y 

def simulacion(path):

   epsilon = 0.1
   with open(path) as f:
      solutions = json.load(f)
   
   for s in solutions:
      instance_name = s["instance_name"]
      instance = "data/instancias-dabia_et_al_2013/" + instance_name + ".json"
      # entrar a la instancia para extraer la ventana de tiempo
      I = json.load(open(instance))
      TW = I["time_windows"]
      idx = 0
      res:dict = {} # clave: instance_name, valor: (num de ruta, time_departures de esa ruta)
      res[instance_name]=[]
      for route in s["routes"]:
         t0 = route["t0"]
         path = route["path"]
         duration = route["duration"]
         time_departures = []
         t_i = t0 
         i = 0
         while i < (len(path)-1):
            time_window = TW[path[i]] #ventana de tiempo del cliente i 
            if time_window[0] > t_i: # si t_i esta fuera de la ventana de tiempo, hay que esperar => sumar la espera
               t_i+=(time_window[0] - t_i)
            y = pwl_f(t_i, path[i], path[i+1], instance_name)
            time_departures.append(((path[i], path[i+1]), (t_i,y)))
            t_i+=y
            i+=1
         # si nos acercamos a la duracion total de la solucion, estamos bien. 
         res[instance_name] = res[instance_name].append((idx, time_departures)) 
         if abs(duration - (t_i - t0)) <= epsilon: 
            print("por ahora funciona. ", instance_name," ruta numero: ", idx)
         else: 
            duracion_nuestra= (t_i - t0)
            print("no funcionó. ", instance_name," ruta numero: ", idx, "duración ruta nuestra: ", duracion_nuestra, "duración posta: ", duration)
         idx+=1
         # calcular t1 = t0 + duracion arco (t0, client) si esta dentro de la ventana de tiempo
      
   return res

if __name__ == "__main__":
   path = 'data/instancias-dabia_et_al_2013/solutions.json'
   simulacion(path)  
