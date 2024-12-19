# TESS calibration tool

Calibration tool for the [TESS-W photometer](https://tess.stars4all.eu/) and derivates.
Works both in command line and GUI mode using Tkinter.

# Installation

```bash
mkdir zptess
cd zptess
uv venv
source .venv/bin/activate
uv pip install zptess
echo "DATABASE_URL=zptess.db" > .env
zptess --version
zptool --version
```

## GUI Mode

1. type `zptess` to launch gui

![Main Panel](doc/image/main.png)
![About](doc/image/about.png)

## CLI Mode

### Summary

1. `zpbegin` to open a calibration batch
2. one or several of `zptessw`, `zptas`, `zptessp` commands for calibration
3. `zpend` to close the calibration batch
4. `zpexport` to export the results and email

### Detailed

#### Open a calibration batch
```bash
zpbegin
2021-11-06 17:36:37,397 [INFO] ============== zptool 0+unknown ==============
2021-11-06 17:36:37,397 [INFO] Opened database file zptess.db
2021-11-06 17:36:37,470 [INFO] A new batch has been opened
```

#### Calibrate one or several photometers

1.a Check the test photometer identity
```bash
zptessw -a {author} -o {offset} -d
````

1.b Alternatively, run a full calibration run without updating neither the database nor photometer ZP
```bash
zptessw -a {author} -o {offset} -t
````

2.a Calibrate and update the Zero Point
```bash
zptessw -a {author} -o {offset} -u
```

2.a Alternatively, run a full calibration run without updating photometer ZP
```bash
zptessw -a {author} -o {offset}
```

#### Close a calibration batch
```bash
zpend
2021-11-06 17:37:40,678 [INFO] ============== zptool 0+unknown ==============
2021-11-06 17:37:40,678 [INFO] Opened database file zptess.db
2021-11-06 17:37:40,739 [INFO] Current open batch has been closed
```
#### Export callibration batch results and optionally email with the results
```bash
zpexport
```