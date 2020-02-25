
# zptess
Command line utility to calibrate TESS-W at LICA

## Installation

```bash
git clone https://github.com/STARS4ALL/zptess.git
sudo python setup.py install
```
or

```bash
pip install --user zptess
```

## Run

See `python -m zptess --help` for help

## The calibration process

Samples from the reference TESS-W and the new TESS-W are taken and stored in circular buffers (default: 25 samples). An estimator of central tendency of frequencies is taken on each buffer (default estimator: median). The standard deviation from this estimator is also computed to asses the quality of readings. If this standard deviation is zero on either buffer, the whole process is discarded. Otherwise, we keep the estimated central tendency of reference and test frequencies and compute a candidate Zero Point.

This process is repeated in a series of rounds (default: 5 rounds) and we select the "best" estimation of frequencies and Zero Point. The best freequency estimation is chosen as the *mode* with a fallback to *median* if mode does not exists.

#### Formulae
```
Mag[ref] = ZP[fict] - 2.5*log10(Freq[ref])
Mag[tst] = ZP[fict] - 2.5*log10(Freq[tst])
Offset   = 2.5*log10(Freq[tst]/Freq[ref])

ZP[calibrated] = ZP[ref] + Offset

where 
	ZP[fict] is a ficticios zero point of 20.50 to compare readings with the TESS Windows utility 
	         by Cristobal García.
	ZP[ref] is the absolute Zero Point of the calibrated TESS-W (20.44) determined by LICA.
```