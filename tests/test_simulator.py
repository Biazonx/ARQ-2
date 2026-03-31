import unittest

from mesif_simulator import SimuladorMESIF


class SimuladorMESIFTests(unittest.TestCase):
    def setUp(self):
        self.sim = SimuladorMESIF(memoria_inicial=[0] * 50)

    def test_primeira_leitura_vira_exclusive(self):
        evento, valor, estado = self.sim.ler(0, 0)

        self.assertEqual("Read Miss", evento)
        self.assertEqual(0, valor)
        self.assertEqual("Exclusivo", estado)

    def test_segunda_leitura_compartilha_bloco(self):
        self.sim.ler(0, 0)

        evento, valor, estado = self.sim.ler(1, 0)
        linha_p0 = self.sim.processadores[0].cache.buscar(0)

        self.assertEqual("Read Miss", evento)
        self.assertEqual(0, valor)
        self.assertEqual("Compartilhado", estado)
        assert linha_p0 is not None
        self.assertEqual("Forward", linha_p0.estado.value)

    def test_escrita_invalida_outras_copias(self):
        self.sim.ler(0, 0)
        self.sim.ler(1, 0)

        evento, estado = self.sim.escrever(1, 0, 2)
        linha_p1 = self.sim.processadores[1].cache.buscar(0)

        self.assertEqual("Write Hit", evento)
        self.assertEqual("Modificado", estado)
        self.assertIsNone(self.sim.processadores[0].cache.buscar(0))
        assert linha_p1 is not None
        assert linha_p1.dados is not None
        self.assertEqual(2, linha_p1.dados[0])


if __name__ == "__main__":
    unittest.main()
