"""Interface gráfica Tkinter para o simulador MESIF."""

from __future__ import annotations

import tkinter as tk
from tkinter import ttk

from .simulator import SimuladorMESIF, normalizar_estado_entrada, traduz_estado_quarto


class MESIFApp:
    def __init__(self, root: tk.Tk):
        self.sim = SimuladorMESIF()
        self.root = root
        root.title("MESIF Simulator")

        self.frame = ttk.Frame(root, padding=10)
        self.frame.grid()

        instrucoes = (
            "Comandos disponíveis:\n"
            "- Processadores válidos: 0, 1 e 2\n"
            "- Ler: informe Processador e Endereço e clique em 'Ler'\n"
            "- Escrever: use 0/disponível, 1/ocupado ou 2/indisponível\n"
            "- Mostrar Cache: exibe os estados MESIF de cada recepcionista\n"
            "- Mostrar RAM: exibe o estado real dos quartos\n"
        )

        ttk.Label(self.frame, text="Processador:").grid(column=0, row=0, sticky="w")
        self.proc = ttk.Entry(self.frame, width=18)
        self.proc.grid(column=1, row=0, padx=4, pady=2)

        ttk.Label(self.frame, text="Endereço (quarto):").grid(column=0, row=1, sticky="w")
        self.end = ttk.Entry(self.frame, width=18)
        self.end.grid(column=1, row=1, padx=4, pady=2)

        ttk.Label(self.frame, text="Novo estado:").grid(column=0, row=2, sticky="w")
        self.valor = ttk.Entry(self.frame, width=18)
        self.valor.grid(column=1, row=2, padx=4, pady=2)

        ttk.Button(self.frame, text="Ler", command=self.ler).grid(column=0, row=3, pady=5)
        ttk.Button(self.frame, text="Escrever", command=self.escrever).grid(column=1, row=3, pady=5)
        ttk.Button(self.frame, text="Mostrar Cache", command=self.mostrar_cache).grid(column=0, row=4, pady=5)
        ttk.Button(self.frame, text="Mostrar RAM", command=self.mostrar_ram).grid(column=1, row=4, pady=5)

        self.output = tk.Text(self.frame, width=82, height=20)
        self.output.grid(column=0, row=5, columnspan=2, pady=10)
        self.log(instrucoes)

    def log(self, text: str) -> None:
        self.output.insert(tk.END, text + "\n")
        self.output.see(tk.END)

    def ler(self) -> None:
        try:
            processador = int(self.proc.get())
            endereco = int(self.end.get())
            evento, valor, estado = self.sim.ler(processador, endereco)
            self.log(f"{evento}: Quarto está {traduz_estado_quarto(valor)} | Estado no cache = {estado}")
        except Exception as erro:
            self.log(f"Erro: {erro}")

    def escrever(self) -> None:
        try:
            processador = int(self.proc.get())
            endereco = int(self.end.get())
            valor = normalizar_estado_entrada(self.valor.get())
            evento, estado = self.sim.escrever(processador, endereco, valor)
            self.log(
                f"{evento}: Novo estado do quarto = {traduz_estado_quarto(valor)} | "
                f"Estado no cache = {estado}"
            )
        except Exception as erro:
            self.log(f"Erro: {erro}")

    def mostrar_cache(self) -> None:
        self.log("--- CACHE ---")
        for processador in self.sim.processadores:
            self.log(f"Processador {processador.id}:")
            for i, linha in enumerate(processador.cache.linhas):
                dados = linha.dados if linha.dados is not None else []
                self.log(
                    f"  Linha {i}: tag={linha.tag} estado={linha.estado.value} "
                    f"fifo={linha.ordem_fifo} dados={dados}"
                )

    def mostrar_ram(self) -> None:
        self.log("--- RAM ---")
        for i, valor in enumerate(self.sim.memoria.dados):
            self.log(f"  Quarto [{i}] = {traduz_estado_quarto(valor)}")


def launch() -> None:
    root = tk.Tk()
    MESIFApp(root)
    root.mainloop()


if __name__ == "__main__":
    launch()
