# MODELS

- TESS-W. The fixed rooftop, wifi photometer
- TESS-P. Handheld TESS device, similar to SQM.
- TAS. 180 degree autoscan TESS. 

# PAYLOAD TYPES

- Old payload format.
This is the old method by old TESS and TESS-W including stars3, the reference photometer

These are lines like the on eblow, intermixed with other output lines (even JSON readings)
```
<fH 41666><tA 02468><tO 02358><aX -0016><aY -0083><aZ 00956><mX 00099><mY -0015><mZ -0520>
or
<fH 04714><tA +2737><tO +2073><mZ -0000>

```

- New JSON payload type, 
They incidentally includes an 'udp' field with the UDP packet count.

```json
{"udp":1646, "rev":2, "name":"stars488", "freq":4852.00, "mag":11.19, "tamb":27.33, "tsky":20.93, "wdBm":0, "ain":446, "ZP":20.40}
```

# TRANSPORT METHODS

We can receive readings by using these transport methods:
- Serial Port
- TCP Port 21
- UDP Port 2255

Serial port is used in rare occasions like stars3, the reference photometer.

TCP is used so far in all firmware versions and mixes readings with other stuff like debug messages
So far they are <CR> terminated lines, except from a bug in 'Nov 25 2021 v 3.2' firmware
which removed <CR> from lines.

UDP transport is available from the beginning and the messages reveived there are purely JSON messages.

# APIS

We can interact with the device to:
1. Get Photometer Info
2. Write new Zero Point values after calibration

## TAS

Photometer Info via Serial Port using primitive request/response text command ('?')
Writting Zero Point via Serial Port using primitive request/response text commands.
Readings as JSON strings via Serial Port

## TESS-P

Photometer Info via Serial Port using primitive request/response text command ('?')
Writting Zero Point via Serial Port using primitive request/response text commands.
Readings as JSON strings via Serial Port

## TESS-W

Photometer Info is done via HTTP
This model is programmed via HTTP GET url http://192.168.4.1/setconst?cons=nn.nn.
Readings in old payload format and (sometimes for the new models) through Serial Port
Readings in both old payload and JSON strings via TCP port 23, intermixed.
Readings as JSON strings via UDP port 5522. (Even an old model like stars61).

To get Phothometer Info, the only way so far is to perform an HTTP request url  "http://192.168.4.1/config"
and parse its HTML contents. There is a provison for an new endpoint "http://192.168.4.1/api/config" 
that would return a JSON text as its body, instead of HTML.
