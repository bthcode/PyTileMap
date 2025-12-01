# Class Overview

```mermaid
---
title: PyTileMap Overview
---
classDiagram
    main -- MapGraphicsView
    QGraphicsView <|-- MapGraphicsView
    MapGraphicsView -- MapGraphicsScene
    QGraphicsScene <|-- MapGraphicsScene 
    MapGraphicsScene -- MapTileSource
    MapGraphicsScene "1" -- "0..n" MapObject
```

# Tile Seqeuence

```mermaid

---
title: Tile Sequence
---
sequenceDiagram
    MapGraphicsScene ->> MapObject sigZoomChanged
    MapTileSource ->> MapGraphicsScene tileReceived
    MapGraphicsScene ->> MapTileSource requestTile

``` 

# Map Objects

```mermaid

---
title: Object Sequence
---
sequenceDiagram
    main ->> MapGraphicsScene addRectShape
    MapGraphicsScene ->> MapGraphicsScene addItem
    MapGraphicsScene ->> QGraphicsScene addItem
    MapGraphicsScene ->> main item

``` 


