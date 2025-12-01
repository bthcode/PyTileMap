```mermaid
---
title: PyTileMap Overview
---
classDiagram
    QGraphicsView <|-- MapGraphicsView
    MapGraphicsView -- MapGraphicsScene
    QGraphicsScene <|-- MapGraphicsScene 
    MapGraphicsScene -- MapTileSource
    MapGraphicsScene "1" -- "0..n" MapObject

```

