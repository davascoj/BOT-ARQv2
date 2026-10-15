"""Fail publication on inconsistent accounting, dates, IDs or browser snapshot."""
from pathlib import Path
import sys
sys.path.insert(0, str(Path(__file__).resolve().parents[1]))
from engine.storage import read_json
from engine.ledger import validate, balances
from engine.policy import can_sell, timestamp


def main():
    book = read_json('historial_senales.json')
    data = read_json('datos_acciones.json')
    paper = read_json('paper/paper_state.json')
    validate(book)
    assert book['schema_version'] == 2
    assert data['run_id'] == book['run_id'] == paper['run_id'] == data['paper_state']['run_id']
    assert len(data['historial']['operaciones']) == len(book['operaciones'])
    b = balances(book)
    assert abs(b['cash'] + b['net_value'] - data['historial']['resumen']['simulacion']['capital_actual_total_estimado']) < 0.01
    assert abs(paper['portfolio']['cash_available_usd'] - b['cash']) < 0.01
    for op in book['operaciones']:
        if op.get('exit_timestamp'):
            assert can_sell(op['fecha_entrada'], timestamp(op['exit_timestamp'])), op['id']
    print(f"Snapshot validated: {book['run_id']}; {len(book['operaciones'])} operations retained")


if __name__ == '__main__':
    main()
