from cdp.cdp import *

#Collection of the data items that can come in a Device Data UWB Packet

class DeviceDataItem():
    type = 0xFF
    definition = [DIVariableLengthBytesAttr('data')]
    
    def __init__(self, tag, ddi_data = None):
        self.tag_id = tag
        self.ddi_size = 0 if ddi_data is None else len(ddi_data)
        self.ddi_data = ddi_data
        self.ddi_name = self.__class__.__name__

    def __str__(self):
        string = "{}, 0x{:02X}".format(CiholasSerialNumber(self.tag_id), self.type)
        for attr in self.definition:
            value = getattr(self, attr.name)

            if attr.is_list:
                value = ", ".join(str(ddi_subdata) for ddi_subdata in value)
            elif attr.format == 's' and isinstance(value, bytes):
                value = value.hex()

            string += ", {}".format(value)
        return string
    
    def __getattr__(self, key):
        if self.ddi_data is not None:
            self._decode()
        else:
            for attr in self.definition:
                # Check if data attribute has not been defined yet before initializing
                # it to its default value
                if not attr.name in dir(self):
                    if attr.is_list:
                        setattr(self, attr.name, list(attr.default))
                    else:
                        setattr(self, attr.name, attr.default)

        if key in dir(self):
            return getattr(self, key)

        # Raise appropriately formatted attribute error
        return object.__getattribute__(self, key)

    def _decode(self):
        for attr in self.definition:
            value, size = attr._decode(self.ddi_data)
            self.ddi_data = self.ddi_data[size:]
            setattr(self, attr.name, value)
        self.ddi_data = None

    def _encode(self):
        data = b''
        for attr in self.definition:
            value = getattr(self, attr.name)
            data += attr._encode(value)
        self.ddi_size = len(data)
        return struct.pack("<HH", self.type, self.ddi_size) + data
        
    
class VersionStringResponse(DeviceDataItem):
    type = 0x01
    definition = [DIUInt8Attr('upgrade_type'),  #0=recovery, 1=bootloader, 2=firmware, 3=almanac
                  DIUInt32Attr('sha1_ending'),  #The Sha1 ending for the upgrade associated with the version string. 
                  DIFixedLengthStrAttr('version', 32)]  #The version string requested by the server.

class MagnetometerCalibrationResponse(DeviceDataItem):
    type = 0x03
    definition = [DIInt16Attr('x'), #Calibration value currently configured for the x-axis, Signed.
                  DIInt16Attr('y'), #Calibration value currently configured for the y-axis, Signed.
                  DIInt16Attr('z')] #Calibration value currently configured for the z-axis, Signed.

class DeviceStatus(DeviceDataItem):
    type = 0x04
    definition = [DIUInt32Attr('memory'),   #How much memory is free
                  DIUInt32Attr('flags'),    #Collection of bits where a 0 is plugged in/external power and 1 is currently charging.
                  DIUInt16Attr('minutes_remaining'),    #Minutes until device shuts down
                  DIUInt8Attr('battery_percentage'),    #255 means there is no battery
                  DIInt8Attr('temperature'),    #In Celsius, Signed
                  DIUInt8Attr('processor_usage'),   #Percentage of processor usage. 255 means unknown.
                  DIVariableLengthBytesAttr('error_led')]   #Array of the error states by their LED pattern.

class GyroscopeCalibrationResponse(DeviceDataItem):
    type = 0x06
    definition = [DIInt32Attr('x'), #Calibration value currently configured for the x-axis, Signed.
                  DIInt32Attr('y'), #Calibration value currently configured for the y-axis, Signed.
                  DIInt32Attr('z'), #Calibration value currently configured for the z-axis, Signed.
                  DIUInt16Attr('scale')]    #Full scale representation in degrees/sec

class PersistentPropertyGetTypesResponse(DeviceDataItem):
    type = 0x07
    definition = [DIUInt16Attr('offset'),   #Marks the index where a new packet must be used
                  DIUInt16Attr('total_types'),  #Total number of types on the device
                  DIUInt16ListAttr('types')]    #Peristent Property Types. Each type is 2B.

class PersistentPropertyGetPropertyResponse(DeviceDataItem):
    type = 0x08
    definition = [DIUInt16Attr('property_id'),  #The property ID being reported
                  DIUInt16Attr('offset'),   #The offset into the property data that the data is being reported
                  DIUInt16Attr('total_size'),   #Total number of bytes for the property
                  DIVariableLengthBytesAttr('data')]    #The data at the specified offset for the property

class BootloaderStatus(DeviceDataItem):
    type = 0x09
    definition = [DIUInt8Attr('last_total_path'),   #The total path RSSI of the last received bootloader packet
                  DIUInt16Attr('time_previous_packet'), #The time in seconds since the last bootloader packet was received
                  DIFixedLengthBytesAttr('sector_flags', 25),   #Flags specifying which sectors have been heard
                  DIUInt8Attr('max_sectors_per_flag'),  #Specifies how many sectors are specified by the first set of flags
                  DIUInt8Attr('last_max_sector_flag')]  #Specifies which flag goes from specifying the "max sectors per flag" to that max minus 1
