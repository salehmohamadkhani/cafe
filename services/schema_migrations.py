from sqlalchemy import inspect, text


def migrate_operational_schema(engine) -> None:
    """Idempotent lightweight migrations shared by default and tenant databases."""
    inspector = inspect(engine)
    if 'material_purchase' in inspector.get_table_names():
        columns = {column['name'] for column in inspector.get_columns('material_purchase')}
        if 'warehouse_id' not in columns:
            with engine.begin() as connection:
                connection.execute(text(
                    'ALTER TABLE material_purchase ADD COLUMN warehouse_id INTEGER REFERENCES warehouse(id)'
                ))
                connection.execute(text(
                    'CREATE INDEX IF NOT EXISTS ix_material_purchase_warehouse_id '
                    'ON material_purchase (warehouse_id)'
                ))
