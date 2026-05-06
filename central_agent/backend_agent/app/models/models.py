from sqlalchemy import Column, Integer, String, Float, ForeignKey, DateTime, Boolean, Index
from sqlalchemy.orm import relationship, declarative_base
from sqlalchemy.sql import func

Base = declarative_base()

class Order(Base):
    __tablename__ = 'orders'

    id = Column(Integer, primary_key=True)
    reference = Column(String(100))
    expediteur = Column(String(200))
    adresse_destinataire = Column(String(500))
    action = Column(String(100))
    contenu = Column(String(500))
    poids = Column(Float)
    date_creation_csv = Column(String(100))
    statut_csv = Column(String(100))
    gouvernorat = Column(String(100))
    
    delivery_value = Column(Float, default=0.0)
    frais_livraison = Column(Float, default=0.0)
    
    lat = Column(Float, nullable=False)
    lng = Column(Float, nullable=False)
    
    priorite = Column(String(50))
    mode_paiement = Column(String(100))
    type_client = Column(String(100))

    status_internal = Column(String(50), default="pending")
    created_at = Column(DateTime(timezone=True), server_default=func.now())

    def __repr__(self):
        return f"<Order(id={self.id}, ref='{self.reference}', status='{self.status_internal}')>"

class Driver(Base):
    __tablename__ = 'drivers'
    
    id = Column(Integer, primary_key=True)
    name = Column(String(100), nullable=False)
    vehicle_capacity = Column(Float, nullable=False, default=500.0)
    current_lat = Column(Float, nullable=True) 
    current_lng = Column(Float, nullable=True)
    is_active = Column(Boolean, default=True)

    def __repr__(self):
        return f"<Driver(id={self.id}, name='{self.name}', active={self.is_active})>"

class Route(Base):
    __tablename__ = 'routes'
    
    id = Column(Integer, primary_key=True)
    driver_id = Column(Integer, ForeignKey('drivers.id'), nullable=False, index=True)
    total_distance_km = Column(Float, default=0.0)
    total_duration_min = Column(Float, default=0.0)
    status = Column(String(50), default="planned")
    created_at = Column(DateTime(timezone=True), server_default=func.now())
    
    # Relationships
    stops = relationship("RouteStop", back_populates="route", cascade="all, delete-orphan")
    profitability = relationship("RouteProfitability", back_populates="route", uselist=False, cascade="all, delete-orphan")

    def __repr__(self):
        return f"<Route(id={self.id}, driver_id={self.driver_id}, status='{self.status}')>"

class RouteStop(Base):
    __tablename__ = 'route_stops'
    
    id = Column(Integer, primary_key=True)
    route_id = Column(Integer, ForeignKey('routes.id'), nullable=False, index=True)
    order_id = Column(Integer, ForeignKey('orders.id'), nullable=False)
    stop_sequence = Column(Integer, nullable=False)
    arrived_at = Column(DateTime(timezone=True), nullable=True)
    
    route = relationship("Route", back_populates="stops")

    def __repr__(self):
        return f"<RouteStop(route_id={self.route_id}, order_id={self.order_id}, seq={self.stop_sequence})>"

class RouteProfitability(Base):
    __tablename__ = 'route_profitability'
    
    id = Column(Integer, primary_key=True)
    route_id = Column(Integer, ForeignKey('routes.id'), nullable=False, index=True)
    total_revenue = Column(Float, default=0.0)
    total_cost = Column(Float, default=0.0)
    gain_net = Column(Float, default=0.0)
    margin_pct = Column(Float, default=0.0)
    calculated_at = Column(DateTime(timezone=True), server_default=func.now())
    
    route = relationship("Route", back_populates="profitability")

    def __repr__(self):
        return f"<RouteProfitability(route_id={self.route_id}, gain={self.gain_net}, margin={self.margin_pct}%)>"