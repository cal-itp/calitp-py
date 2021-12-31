# flake8: noqa

# +
from ipyleaflet import Map, Marker

center = (52.204793, 360.121558)
m = Map(center=center, zoom=15)
marker = Marker(location=center, draggable=True)
m.add_layer(marker)
display(m)
