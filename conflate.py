#!/usr/bin/python

import osgeo.ogr
import OsmApi
import sys

def notice(level, desc, feature=None, action=None):
  if feature == None and level != "OK":
    sys.stderr.write( level.upper() + " " + desc )
  elif feature != None:
    feature['tag']['NOTICE'] = desc
    feature['tag']['NOTICE_LEVEL'] = level.upper()
    feature['tag']['source'] = "http://www.unitar.org/unosat/node/44/1809"
    print output_feature_as_osm_xml( feature, action )

def load_import_features(shapePath, id_index):
  shapeData = osgeo.ogr.Open(shapePath)
  layer = shapeData.GetLayer()

  #layer_defn = layer.GetLayerDefn()
  #field_names = [layer_defn.GetFieldDefn(i).GetName() for i in range(layer_defn.GetFieldCount())]

  shapefile_features = {}
  for index in xrange(layer.GetFeatureCount()):
    feature = layer.GetFeature(index)
  #  geometry = feature.GetGeometryRef()
  #  definition = feature.GetDefnRef()
    objectid = feature.GetFieldAsString(id_index)
    shapefile_features[ objectid ] = feature

  return shapefile_features

def load_osm_features(osmPath, idtag):
  osm_features = {}
  with open(osmPath, 'r') as f:
    osmString = f.read()
  f.closed
  data = MyApi.ParseOsm(osmString)
  for index in xrange(len(data)):
    if idtag in data[index]['data']['tag']:
      objectid = data[index]['data']['tag'][idtag]
      osm_features[ objectid ] = data[index]['data']

  return osm_features

def load_non_import_osm_features(osmPath, idtag):
  osm_features = {}
  with open(osmPath, 'r') as f:
    osmString = f.read()
  f.closed
  data = MyApi.ParseOsm(osmString)
  for index in xrange(len(data)):
    if idtag not in data[index]['data']['tag'] and "building" in data[index]['data']['tag']:
      osm_features[ data['id'] ] = data[index]['data']
  return osm_features

def check_import_feature_status( feature ):
  shelter_status = feature.GetFieldAsString(13)
  sensor_date = feature.GetFieldAsString(3)
  closed_date = feature.GetFieldAsString(14)

  if shelter_status == '1' and sensor_date != import_date:  
    return "EXISTING"
  elif shelter_status == '1' and sensor_date == import_date:
    return "ADDITION"
  elif shelter_status == "2" and closed_date == import_date:
    return "DELETE"
  # What about testing for past deletes

#"building" Structure_, 15 (1=shelther, 2=administrative)
#"source"=http://www.unitar.org/unosat/node/44/1773
#"unosat:acquisition_date" Sensor_Dat, 3
#"unosat:event_code" EventCode, 10
#"unosat:objectid" OBJECTID, 0
# Shelter_St, 13 (1=existing, 2=deleted)
# ShelterClo, 14 (Date shelter closed)  
def transform_import_feature_to_osm( import_feature ):
  osm_feature = {}

  geometry = import_feature.GetGeometryRef()
  osm_feature['lat'] = geometry.GetY()
  osm_feature['lon'] = geometry.GetX()

  osm_feature['tag'] = {}

  if import_feature.GetFieldAsString(15) == "1":
    osm_feature['tag']['building'] = 'shelter'
  elif import_feature.GetFieldAsString(15) == "2":
    osm_feature['tag']['building'] = 'administrative'
  else:
    notice('warn','Unknown Structure_ value: ' + import_feature.GetFieldAsString(15))

  osm_feature['tag']['unosat:acquisition_date'] = import_feature.GetFieldAsString(3)
  osm_feature['tag']['unosat:event_code'] = import_feature.GetFieldAsString(10)
  osm_feature['tag']['unosat:objectid'] = import_feature.GetFieldAsString(0)

  return osm_feature

def check_osm_feature_changed( osm_feature ):
  #import_feature_as_osm = transform_import_feature_to_osm( import_feature )
  #attr_list = ['lat','lon','building','unosat:acquisition_date','unosat:event_code']
  #if import_feature['building'] == osm_feature['building']
  # TODO proper date compare
  if 'timestamp' in osm_feature and osm_feature['timestamp'] > last_import_date:
    return true
  else:
    return None

def print_osm_header():
  print "<?xml version='1.0' encoding='UTF-8'?><osm version='0.6' upload='false' generator='conflate.py'>"
def print_osm_footer():
  print "</osm>"

def output_feature_as_osm_xml( feature, action=None ):
  global create_id_index
  if action == "create":
    feature['id'] = create_id_index
    create_id_index -= 1
  return MyApi._XmlBuild('node', feature, False, action)

MyApi = OsmApi.OsmApi()
create_id_index = -1
import_date = '2013/08/25' #Import data created by UNOSAT
last_import_date = '2013/08/31' #Prior import upload to OSM
import_features = load_import_features('20130825-UNOSAT/Al_Zaatari_Shelters.shp', 0)
osm_features = load_osm_features('zaatari.osm', 'unosat:objectid')

print_osm_header()

for k in import_features.keys():
  feature_status = check_import_feature_status( import_features[ k ] )
  if feature_status == "EXISTING":
    if k in osm_features:
      if check_osm_feature_changed( osm_features[ k ] ):
        notice("ALERT", "OSM feature changed", osm_features[ k ]) #Output OSM feature, with NOTICE tag
      else:
        notice("OK", "Keeping feature: " + k) #Do nada
    else:
      notice("ERROR", "Existing feature missing from past import",  transform_import_feature_to_osm(import_features[ k ]), "create") #Output Import feature, with NOTICE tag

  elif feature_status == "ADDITION":
    if k in osm_features:
      notice("ERROR", "New features present in past import", osm_features[ k ]) #Output OSM feature, with NOTICE tag
    else:
      notice("OK", "Add new feature",  transform_import_feature_to_osm( import_features[ k ] ), "create") #Output Import Add

  elif feature_status == "DELETE":
    if k in osm_features:
      if check_osm_feature_changed( osm_features[ k ] ):
        notice("ALERT", "OSM feature changed but deleted in import", osm_features[ k ]) #Output OSM feature, with NOTICE tag
      else:
        notice("OK", "Delete feature", osm_features[ k ], "delete") #Output OSM Delete
    else:
      notice("ERROR", "Deleted feature missing in past import: " + k) #

# Check OSM features matching tags (building=*) that are not from UNOSAT import
non_import_osm_features = load_non_import_osm_features('zaatari.osm', 'unosat:objectid')
for k in non_import_osm_features.keys():
  notice("ALERT", "OSM feature created :" + k, non_import_osm_features[ k ]) #Output OSM feature, with NOTICE tag

print_osm_footer()
