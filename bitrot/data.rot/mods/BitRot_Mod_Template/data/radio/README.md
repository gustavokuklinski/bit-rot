# Creating Radios

Read and understand the craft types.

## radio/[TYPE: text].xml

radio/military_satellite_radio.xml
```xml
<?xml version="1.0" encoding="UTF-8"?>
<radio name="Military Satellite" frequency="120.0" stream="[weather]">
    <stream text="[STATIC]...[COF]...[COF]...This is the safety broadcast channel satellite...[STATIC]\n[STATIC]...Tropical, raining forming, expected at: {rain_time}...[COF]...[STATIC]" />
</radio>
```