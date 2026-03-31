# MESIF Hotel Simulator

Simulador em Python do protocolo de coerência de cache **MESIF**, usando a metáfora de recepcionistas controlando quartos de um hotel.

## Estrutura do repositório

```text
ARQ-2/
├── README.md
├── pyproject.toml
├── .gitignore
├── run_terminal.py
├── run_gui.py
├── mesif_simulator/
│   ├── __init__.py
│   ├── __main__.py
│   ├── simulator.py
│   └── gui.py
└── tests/
    └── test_simulator.py
```

## Como executar

### Terminal

```bash
python run_terminal.py
```

### Terminal técnico

```bash
python run_terminal.py --menu
```

### Testes automáticos da simulação

```bash
python run_terminal.py --testes
```

### Interface gráfica

```bash
python run_gui.py
```

## O que o projeto mostra

- leitura e escrita com estados `MESIF`
- política de substituição `FIFO`
- política de escrita `write-back`
- memória principal com 50 posições
- três processadores simulando recepcionistas
