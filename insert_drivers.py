import sys
sys.path.insert(0, 'central_agent/backend_agent')

from app.models.models import Driver
from app.core.database import SessionLocal

session = SessionLocal()

drivers = [
    {'id': 1, 'name': 'Livreur Ahmad', 'vehicle_capacity': 500, 'current_lat': 36.806, 'current_lng': 10.181},
    {'id': 2, 'name': 'Livreur Ali', 'vehicle_capacity': 500, 'current_lat': 36.806, 'current_lng': 10.181},
    {'id': 5, 'name': 'Livreur Salah', 'vehicle_capacity': 500, 'current_lat': 36.806, 'current_lng': 10.181},
    {'id': 3, 'name': 'Livreur Karim', 'vehicle_capacity': 500, 'current_lat': 36.806, 'current_lng': 10.181},
    {'id': 4, 'name': 'Livreur Yessin', 'vehicle_capacity': 500, 'current_lat': 36.806, 'current_lng': 10.181}
]

for d in drivers:
    existing = session.query(Driver).filter(Driver.id == d['id']).first()
    if not existing:
        driver = Driver(**d)
        session.add(driver)
        print("Added: " + d['name'])
    else:
        print("Already exists: " + d['name'])

session.commit()
session.close()
print("Drivers inserted!")
