"""Núcleo do simulador MESIF e interfaces de terminal."""

from __future__ import annotations

import argparse
import random
from dataclasses import dataclass
from enum import Enum
from typing import List, Optional, Tuple

TAMANHO_RAM = 50
TAMANHO_CACHE = 5
TAMANHO_BLOCO = 5
NUM_PROCESSADORES = 3

ESTADOS_QUARTO = {
    0: "Disponível",
    1: "Ocupado",
    2: "Indisponível",
}


class Estados(Enum):
    MODIFIED = "Modificado"
    FORWARD = "Forward"
    EXCLUSIVE = "Exclusivo"
    SHARED = "Compartilhado"
    INVALID = "Inválido"


@dataclass
class LinhaCache:
    """Representa uma linha de cache."""

    tag: Optional[int] = None
    dados: Optional[List[int]] = None
    estado: Estados = Estados.INVALID
    ordem_fifo: int = -1


class MemoriaRAM:
    """Representa a memória principal compartilhada."""

    def __init__(
        self,
        tamanho: int = TAMANHO_RAM,
        dados_iniciais: Optional[List[int]] = None,
    ):
        self.tamanho = tamanho
        if dados_iniciais is None:
            self.dados = [random.randint(0, 2) for _ in range(tamanho)]
        else:
            if len(dados_iniciais) < tamanho:
                raise ValueError("A memória inicial deve ter pelo menos 50 posições.")
            self.dados = list(dados_iniciais[:tamanho])

    def ler_bloco(self, indice_bloco: int) -> List[int]:
        inicio = indice_bloco * TAMANHO_BLOCO
        fim = min(inicio + TAMANHO_BLOCO, self.tamanho)
        return self.dados[inicio:fim]

    def escrever_bloco(self, indice_bloco: int, dados_bloco: List[int]) -> None:
        inicio = indice_bloco * TAMANHO_BLOCO
        for i, valor in enumerate(dados_bloco):
            if inicio + i < self.tamanho:
                self.dados[inicio + i] = valor


class Cache:
    """Cache privada de um processador com substituição FIFO."""

    def __init__(self, tamanho: int):
        self.tamanho = tamanho
        self.linhas: List[LinhaCache] = [LinhaCache() for _ in range(tamanho)]
        self._contador_fifo = 0

    def buscar(self, tag: int) -> Optional[LinhaCache]:
        for linha in self.linhas:
            if linha.tag == tag and linha.estado != Estados.INVALID:
                return linha
        return None

    def linhas_validas(self) -> List[LinhaCache]:
        return [linha for linha in self.linhas if linha.estado != Estados.INVALID]

    def alocar_linha(self) -> LinhaCache:
        invalidas = [linha for linha in self.linhas if linha.estado == Estados.INVALID]
        if invalidas:
            return invalidas[0]
        return min(self.linhas_validas(), key=lambda linha: linha.ordem_fifo)

    def substituir(
        self,
        memoria: MemoriaRAM,
        nova_tag: int,
        novos_dados: List[int],
        novo_estado: Estados,
    ) -> LinhaCache:
        linha = self.alocar_linha()

        if linha.estado == Estados.MODIFIED and linha.tag is not None and linha.dados is not None:
            memoria.escrever_bloco(linha.tag, linha.dados)

        linha.tag = nova_tag
        linha.dados = novos_dados[:]
        linha.ordem_fifo = self._contador_fifo
        self._contador_fifo += 1
        linha.estado = novo_estado
        return linha


class Processador:
    """Representa um processador com sua própria cache."""

    def __init__(self, id_proc: int):
        self.id = id_proc
        self.cache = Cache(TAMANHO_CACHE)


def traduz_estado_quarto(valor: int) -> str:
    return ESTADOS_QUARTO.get(valor, f"Desconhecido ({valor})")


def normalizar_estado_entrada(entrada: str | int) -> int:
    valor = str(entrada).strip().lower()
    mapa = {
        "0": 0,
        "disponivel": 0,
        "disponível": 0,
        "1": 1,
        "ocupado": 1,
        "2": 2,
        "indisponivel": 2,
        "indisponível": 2,
    }
    if valor not in mapa:
        raise ValueError("Use 0/disponível, 1/ocupado ou 2/indisponível.")
    return mapa[valor]


class SimuladorMESIF:
    """Simulador do protocolo MESIF para coerência de cache."""

    def __init__(self, memoria_inicial: Optional[List[int]] = None):
        self.memoria = MemoriaRAM(dados_iniciais=memoria_inicial)
        self.processadores = [Processador(i) for i in range(NUM_PROCESSADORES)]

    def _validar_processador(self, id_proc: int) -> None:
        if id_proc < 0 or id_proc >= len(self.processadores):
            raise ValueError(f"Processador inválido: {id_proc}. Use 0 a {NUM_PROCESSADORES - 1}.")

    def _bloco_e_offset(self, endereco: int) -> Tuple[int, int]:
        if endereco < 0 or endereco >= self.memoria.tamanho:
            raise ValueError("Endereço fora dos limites da RAM")
        return endereco // TAMANHO_BLOCO, endereco % TAMANHO_BLOCO

    def _localizar_copias(self, tag: int) -> List[LinhaCache]:
        copias = []
        for processador in self.processadores:
            linha = processador.cache.buscar(tag)
            if linha:
                copias.append(linha)
        return copias

    def _garantir_unico_forward(self, tag: int) -> None:
        linhas = self._localizar_copias(tag)
        forwards = [linha for linha in linhas if linha.estado == Estados.FORWARD]

        if len(forwards) > 1:
            forwards.sort(key=lambda linha: linha.ordem_fifo)
            for linha in forwards[1:]:
                linha.estado = Estados.SHARED

        if not forwards and linhas:
            linhas.sort(key=lambda linha: linha.ordem_fifo)
            linhas[0].estado = Estados.FORWARD

    @staticmethod
    def _dados_da_linha(linha: LinhaCache) -> List[int]:
        if linha.dados is None:
            raise RuntimeError("Linha de cache sem dados válidos.")
        return linha.dados

    def ler(self, id_proc: int, endereco: int):
        """Devolve `(evento, valor, estado_cache)` para uma leitura."""

        self._validar_processador(id_proc)
        tag, offset = self._bloco_e_offset(endereco)
        proc = self.processadores[id_proc]
        linha = proc.cache.buscar(tag)

        if linha:
            valor = self._dados_da_linha(linha)[offset]
            return "Read Hit", valor, linha.estado.value

        copias = self._localizar_copias(tag)
        if not copias:
            bloco = self.memoria.ler_bloco(tag)
            nova = proc.cache.substituir(self.memoria, tag, bloco, Estados.EXCLUSIVE)
            return "Read Miss", self._dados_da_linha(nova)[offset], nova.estado.value

        provedor = copias[0]
        bloco = self._dados_da_linha(provedor)[:]

        if provedor.estado == Estados.MODIFIED:
            self.memoria.escrever_bloco(tag, self._dados_da_linha(provedor))
            provedor.estado = Estados.FORWARD
        elif provedor.estado in (Estados.EXCLUSIVE, Estados.SHARED):
            provedor.estado = Estados.FORWARD

        for outra in copias[1:]:
            if outra.estado == Estados.FORWARD:
                outra.estado = Estados.SHARED
            elif outra.estado == Estados.MODIFIED:
                self.memoria.escrever_bloco(tag, self._dados_da_linha(outra))
                outra.estado = Estados.SHARED

        nova = proc.cache.substituir(self.memoria, tag, bloco, Estados.SHARED)
        self._garantir_unico_forward(tag)
        return "Read Miss", self._dados_da_linha(nova)[offset], nova.estado.value

    def escrever(self, id_proc: int, endereco: int, valor: int):
        """Devolve `(evento, estado_cache)` para uma escrita."""

        self._validar_processador(id_proc)
        if valor not in ESTADOS_QUARTO:
            raise ValueError("O valor do quarto deve ser 0, 1 ou 2.")

        tag, offset = self._bloco_e_offset(endereco)
        proc = self.processadores[id_proc]
        linha = proc.cache.buscar(tag)

        if linha:
            if linha.estado in (Estados.SHARED, Estados.FORWARD, Estados.EXCLUSIVE):
                for processador in self.processadores:
                    if processador.id == id_proc:
                        continue
                    outra = processador.cache.buscar(tag)
                    if outra and outra.estado != Estados.INVALID:
                        if outra.estado == Estados.MODIFIED:
                            self.memoria.escrever_bloco(tag, self._dados_da_linha(outra))
                        outra.estado = Estados.INVALID
                linha.estado = Estados.MODIFIED

            self._dados_da_linha(linha)[offset] = valor
            return "Write Hit", linha.estado.value

        copias = self._localizar_copias(tag)
        for copia in copias:
            if copia.estado == Estados.MODIFIED:
                self.memoria.escrever_bloco(tag, self._dados_da_linha(copia))
            copia.estado = Estados.INVALID

        bloco = self.memoria.ler_bloco(tag)
        bloco[offset] = valor
        nova = proc.cache.substituir(self.memoria, tag, bloco, Estados.MODIFIED)
        return "Write Miss", nova.estado.value

    def print_caches(self) -> None:
        for processador in self.processadores:
            print(f"Processador {processador.id}:")
            for i, linha in enumerate(processador.cache.linhas):
                dados = linha.dados if linha.dados is not None else []
                print(
                    f"  Linha {i}: tag={linha.tag} estado={linha.estado.value} "
                    f"fifo={linha.ordem_fifo} dados={dados}"
                )
            print()

    def print_ram(self) -> None:
        print("RAM:")
        for i, valor in enumerate(self.memoria.dados):
            print(f"  [{i}]={valor} ({traduz_estado_quarto(valor)})")
        print()


def menu() -> None:
    sim = SimuladorMESIF()
    print("Simulador MESIF iniciado.")
    print("Comandos: ler <proc> <end> | escrever <proc> <end> <valor> | cache | ram | sair")

    while True:
        cmd = input("> ").strip().split()
        if not cmd:
            continue

        op = cmd[0].lower()
        try:
            if op == "ler" and len(cmd) == 3:
                proc = int(cmd[1])
                endereco = int(cmd[2])
                evento, valor, estado = sim.ler(proc, endereco)
                print(f"{evento} valor={valor} ({traduz_estado_quarto(valor)}) estado={estado}")
            elif op == "escrever" and len(cmd) == 4:
                proc = int(cmd[1])
                endereco = int(cmd[2])
                valor = normalizar_estado_entrada(cmd[3])
                evento, estado = sim.escrever(proc, endereco, valor)
                print(f"{evento} novo_estado={estado}")
            elif op == "cache":
                sim.print_caches()
            elif op == "ram":
                sim.print_ram()
            elif op in {"sair", "quit"}:
                break
            else:
                print("Comando inválido.")
        except Exception as erro:
            print(f"Erro: {erro}")


def testes_automaticos() -> None:
    """Executa uma demonstração simples do protocolo MESIF."""

    sim = SimuladorMESIF()
    print("[TEST] Estado inicial RAM (parcial):", sim.memoria.dados[:15])

    end_a = 0
    end_b = TAMANHO_BLOCO * 1
    end_c = TAMANHO_BLOCO * 2
    end_d = TAMANHO_BLOCO * 3
    end_e = TAMANHO_BLOCO * 4

    print("[TEST] Preenchendo cache do P0 com 5 blocos via leitura (RM->E)...")
    for endereco in [end_a, end_b, end_c, end_d, end_e]:
        evento, valor, estado = sim.ler(0, endereco)
        print(f"  ler P0,{endereco}: {evento} estado={estado} valor={valor}")

    print("[TEST] Cache P0 após preenchimento:")
    sim.print_caches()

    print("[TEST] Write Hit em P0 bloco A (WH -> M)...")
    evento, estado = sim.escrever(0, end_a, 2)
    print(f"  escrever P0,{end_a}: {evento} estado={estado}")

    end_f = TAMANHO_BLOCO * 5
    print("[TEST] Ler bloco F para provocar evicção FIFO em P0...")
    evento, valor, estado = sim.ler(0, end_f)
    print(f"  ler P0,{end_f}: {evento} estado={estado} valor={valor}")

    bloco_a_idx, _ = sim._bloco_e_offset(end_a)
    print("[TEST] RAM bloco A após possível write-back:")
    print(sim.memoria.ler_bloco(bloco_a_idx))

    print("[TEST] P1 lendo bloco C para compartilhar (RM -> S/F)...")
    evento, valor, estado = sim.ler(1, end_c)
    print(f"  ler P1,{end_c}: {evento} estado={estado} valor={valor}")
    sim.print_caches()

    print("[TEST] P1 escreve no bloco C (WH/WM -> M)...")
    evento, estado = sim.escrever(1, end_c, 1)
    print(f"  escrever P1,{end_c}: {evento} estado={estado}")
    sim.print_caches()

    print("[TEST] RAM (parcial) após sequência:")
    print(sim.memoria.dados[:15])


def recepcao() -> None:
    """Interface temática do hotel para demonstrar o protocolo."""

    sim = SimuladorMESIF()
    print("Iniciando simulação de controle de quartos de hotel com MESIF...")
    print("c <recepcionista> <quarto> | m <recepcionista> <quarto> <estado> | a | r | s")

    while True:
        cmd = input("> ").strip().split()
        if not cmd:
            continue

        op = cmd[0].lower()
        try:
            if op == "c" and len(cmd) == 3:
                recep = int(cmd[1]) - 1
                quarto = int(cmd[2]) - 1
                evento, valor, estado = sim.ler(recep, quarto)
                print(
                    f"{evento}; quarto está {traduz_estado_quarto(valor)}; "
                    f"estado do cache {estado}"
                )
            elif op == "m" and len(cmd) == 4:
                recep = int(cmd[1]) - 1
                quarto = int(cmd[2]) - 1
                novo_estado = normalizar_estado_entrada(cmd[3])
                evento, estado = sim.escrever(recep, quarto, novo_estado)
                print(f"{evento}; novo estado cache: {estado}")
            elif op == "a":
                for processador in sim.processadores:
                    print(f"Recepcionista {processador.id + 1}:")
                    for i, linha in enumerate(processador.cache.linhas):
                        dados = linha.dados if linha.dados is not None else []
                        print(
                            f"  Linha {i}: andar={linha.tag} estado={linha.estado.value} "
                            f"fifo={linha.ordem_fifo} dados={dados}"
                        )
            elif op == "r":
                print("Estado dos Quartos (RAM):")
                for i, valor in enumerate(sim.memoria.dados):
                    print(f"  Quarto [{i + 1}]: {traduz_estado_quarto(valor)}")
            elif op in {"s", "sair", "quit"}:
                break
            else:
                print("Comando inválido.")
        except Exception as erro:
            print(f"Erro: {erro}")


def build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(description="Simulador do protocolo MESIF.")
    parser.add_argument(
        "--menu",
        action="store_true",
        help="abre o menu técnico de leitura e escrita por endereço",
    )
    parser.add_argument(
        "--testes",
        action="store_true",
        help="executa uma demonstração automática",
    )
    return parser


def main(argv: Optional[list[str]] = None) -> None:
    args = build_parser().parse_args(argv)

    if args.testes:
        testes_automaticos()
    elif args.menu:
        menu()
    else:
        recepcao()


# Compatibilidade com o nome anterior.
testes_automáticos = testes_automaticos


if __name__ == "__main__":
    main()