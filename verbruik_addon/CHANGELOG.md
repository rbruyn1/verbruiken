# Changelog

## 0.1.3
- Fix: nav-links braken uit de ingress-iframe naar de kale HA-interface
  (Flask respecteerde de `X-Ingress-Path`-header van Supervisor niet).

## 0.1.2
- Fix: `s6-overlay-suexec: fatal: can only run as pid 1` — `init: false`
  toegevoegd aan config.yaml (baseimage brengt al eigen s6-init mee).

## 0.1.1
- Fix: `build.yaml` toegevoegd (BUILD_FROM per architectuur ontbrak).
- Dockerfile vereenvoudigd op de `-base-python`-baseimage.

## 0.1.0
- Eerste versie: maand- en jaaroverzicht voor Tienen en Binkom,
  bestaande Excel-historiek gemigreerd.
