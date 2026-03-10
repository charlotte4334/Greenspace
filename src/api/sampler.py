
from config.settings import  UBERBAUUNG_MAP , GEMEINDE_MAP, NDVI_MAP_NIR, NDVI_MAP_RED
import matplotlib.pyplot as plt
import geopandas as gpd
import rasterio 
import numpy as np
from rasterio.mask import mask
from shapely.geometry import Point



def sample_locations(map_data="KZ_UBERBAUUNG", method="random", n=100,plot= False, **kwargs):
    """
    Samples locations from map_data.

    Parameters:
        map_data : The map that is sampled on
        method   : str, sampling strategy
        n        : number of samples
        kwargs   : optional parameters for specific methods

    Returns:
        List of (lat, lon) tuples
    """

    map, transform, raster_crs = load_map_data(map_data)

    if method == "random":
        sampled_coordinates, rows_s, cols_s = random_sampling(map, transform, raster_crs,map_data, n)
        if plot:
            if map_data == "KZ_UBERBAUUNG_NDVI":
                plot_samples_on_map(map, rows_s, cols_s)
            elif map_data == "KZ_UBERBAUUNG":
                plot_samples_on_vector_map(map, rows_s, cols_s)
        return sampled_coordinates
    else:
        raise ValueError(f"Unknown sampling method: {method}")


    


def random_sampling(map, transform, raster_crs,map_data,n):
        # Implement random sampling logic here

        # 1) 
        

        if map_data == "KZ_UBERBAUUNG_NDVI":
            map_2d = map.squeeze()

            # 2) Sample random points anywhere inside raster bounds (map coordinates)
            height, width = map_2d.shape
            left, bottom, right, top = rasterio.transform.array_bounds(height, width, transform)
            xs = np.random.uniform(left, right, size=n)
            ys = np.random.uniform(bottom, top, size=n)

            # 3) Convert sampled map coordinates to pixel indices (for plotting)
            rows_s, cols_s = rasterio.transform.rowcol(transform, xs, ys)

            # 5) Build GeoDataFrame in raster CRS
            gdf_samples = gpd.GeoDataFrame(
                geometry=gpd.points_from_xy(xs, ys),
                crs=raster_crs
            )

            # 6) Convert to latitude / longitude
            gdf_samples_ll = gdf_samples.to_crs(epsg=4326)

            # 7) Extract (lat, lon) tuples if needed
            sampled_coordinates = [
                (pt.y, pt.x) for pt in gdf_samples_ll.geometry
            ]
        
       
            return sampled_coordinates, rows_s, cols_s
        elif map_data == "KZ_UBERBAUUNG":
            #No raster coordinates to convert, just return the sampled points in the original CRS of the map
        # return the coordinates in origian CRS for plotting
            #rn the real coordinates fo
            if map.empty:
                raise ValueError("No geometries available for KZ_UBERBAUUNG sampling")

            target_geometries = map.geometry.union_all()
            minx, miny, maxx, maxy = target_geometries.bounds

            sampled_points = []
            max_attempts = max(n * 100, 1000)
            attempts = 0
            
            
            while len(sampled_points) < n and attempts < max_attempts:
                batch_size = min((n - len(sampled_points)) * 4, 5000)
                xs = np.random.uniform(minx, maxx, batch_size)
                ys = np.random.uniform(miny, maxy, batch_size)

                for x, y in zip(xs, ys):
                    point = Point(x, y)
                    if target_geometries.contains(point):
                        sampled_points.append(point)
                        if len(sampled_points) == n:
                            break

                attempts += batch_size
            
            

            if len(sampled_points) < n:
                raise ValueError(
                    f"Could only sample {len(sampled_points)} points inside KZ_UBERBAUUNG after {attempts} attempts"
                )

            gdf_samples = gpd.GeoDataFrame(geometry=sampled_points, crs=map.crs)
            gdf_samples_ll = gdf_samples.to_crs(epsg=4326)

            sampled_coordinates = [(pt.y, pt.x) for pt in gdf_samples_ll.geometry]
            rows_s = np.asarray([pt.y for pt in sampled_points])
            cols_s = np.asarray([pt.x for pt in sampled_points])
            return sampled_coordinates, rows_s, cols_s

        else:
            raise ValueError(f"Unknown map_data: {map_data}")

            



def clip_raster(red_path, nir_path, vector_gdf):

    with rasterio.open(red_path) as red_src:
        
    # convert vector_gdf to the same CRS as the raster
        raster_crs = red_src.crs
        vector_gdf = vector_gdf.to_crs(raster_crs)
        
        # transform with rasterio 
        masked, transform = mask(red_src, vector_gdf.geometry,crop=True)

    # Repeat for nir band
    with rasterio.open(nir_path) as nir_src:
        vector_gdf = vector_gdf.to_crs(nir_src.crs)
        masked_nir, transform = mask(nir_src, vector_gdf.geometry,crop=True)

    # Now calculate the NDVI (safe division to avoid warnings on zero denominator)
    red = masked.astype(np.float32)
    nir = masked_nir.astype(np.float32)
    denominator = nir + red

    ndvi = np.full_like(denominator, np.nan, dtype=np.float32)
    with np.errstate(divide="ignore", invalid="ignore"):
        np.divide(nir - red, denominator, out=ndvi, where=denominator != 0)

    #Apply threshold to ndvi
    ndvi_thresholded = ndvi > 0.3   

    return ndvi_thresholded, transform, raster_crs


#Sampling urban areas 

def load_map_data(map_name):

    if map_name == "KZ_UBERBAUUNG_NDVI":
        #1.----------------- Zurich Kant": boundary --------------------

        kantone = gpd.read_file(GEMEINDE_MAP, layer="UP_KANTON_F")
        zurich_boundary =  kantone[kantone['ABKUERZUNG'] == 'ZH']

        #1.----------------- Uberbauung --------------------

        gdf_u = gpd.read_file(UBERBAUUNG_MAP, layer="RP_UEBERBAUUNGSSTAND_F")
        uberbaut = gdf_u[gdf_u['ABC'] == 'B'] # Filter for überbaut areas (ABC == "B")  (Überbaut)


        #1.----------------- Dilated map --------------------


        # Ensure CRS is in meters (CH1903+ / LV95)
        zurich_uberbaut_meters = uberbaut.to_crs("EPSG:2056")  # LV95
        zurich_boundary_meters = zurich_boundary.to_crs("EPSG:2056")

        # Buffer polygons outward 100 m
        zurich_dilated = zurich_uberbaut_meters.buffer(100)

        # Convert back to GeoDataFrame
        zurich_dilated_gdf = gpd.GeoDataFrame(geometry=zurich_dilated, crs=zurich_uberbaut_meters.crs)

        # Constrain dilated areas to Zurich canton boundary (clip to canton border)
        zurich_dilated_clipped = gpd.overlay(zurich_dilated_gdf, zurich_boundary_meters, how='intersection')


        #1.----------------- Raster clipping map --------------------

        # Clip NIR and red raster with Zurich_dilated_clipped

        ndvi_zurich_k_urban, transform, raster_crs = clip_raster(NDVI_MAP_RED, NDVI_MAP_NIR, zurich_dilated_clipped)
        return ndvi_zurich_k_urban, transform, raster_crs 

    elif map_name == "KZ_UBERBAUUNG":
         #1.----------------- Zurich Kant": boundary --------------------

        kantone = gpd.read_file(GEMEINDE_MAP, layer="UP_KANTON_F")
        zurich_boundary =  kantone[kantone['ABKUERZUNG'] == 'ZH']

        #1.----------------- Uberbauung --------------------

        gdf_u = gpd.read_file(UBERBAUUNG_MAP, layer="RP_UEBERBAUUNGSSTAND_F")
        uberbaut = gdf_u[gdf_u['ABC'] == 'B'] # Filter for überbaut areas (ABC == "B")  (Überbaut)


        #1.----------------- Dilated map --------------------


        # Ensure CRS is in meters (CH1903+ / LV95)
        zurich_uberbaut_meters = uberbaut.to_crs("EPSG:2056")  # LV95
        zurich_boundary_meters = zurich_boundary.to_crs("EPSG:2056")

        # Buffer polygons outward 100 m
        zurich_dilated = zurich_uberbaut_meters.buffer(100)

        # Convert back to GeoDataFrame
        zurich_dilated_gdf = gpd.GeoDataFrame(geometry=zurich_dilated, crs=zurich_uberbaut_meters.crs)

        return zurich_dilated_gdf, None, None

    else:
        #error message
        raise ValueError(f"Unknown map name: {map_name}")





def plot_samples_on_map(map, rows_s, cols_s):
    """
    Plots sampled points on the map for visualization.

    Parameters:
        map : The map to plot on
        sampled_coordinates : List of (lat, lon) tuples
    """
    # Implement plotting logic here (e.g., using matplotlib or geopandas)
    plt.imshow(map[0], cmap='Greens')
    plt.scatter(cols_s, rows_s, c='red', marker='o', s=1)
    plt.title("NDVI Thresholded Map of Zurich Gemeinde with Sampled Points")
    plt.axis('off')
    plt.show()


def plot_samples_on_vector_map(map_gdf, rows_s, cols_s):
    fig, ax = plt.subplots(figsize=(8, 8))
    map_gdf.plot(ax=ax, color='lightgrey', edgecolor='black', linewidth=0.3)

    sample_points = gpd.GeoDataFrame(
        geometry=gpd.points_from_xy(cols_s, rows_s),
        crs=map_gdf.crs
    )
    sample_points.plot(ax=ax, color='red', markersize=4)

    ax.set_title("Sampled Points in KZ_UBERBAUUNG")
    ax.set_axis_off()
    plt.show()