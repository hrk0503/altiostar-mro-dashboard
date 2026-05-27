"""Tests for Spectrum Agent — 3GPP domain validation."""


from src.agents.spectrum import SpectrumAgent


class TestSpectrumAgent:
    def setup_method(self):
        self.agent = SpectrumAgent()

    def test_valid_cio(self):
        assert self.agent.validate_cio_range(0.0) is True
        assert self.agent.validate_cio_range(-24.0) is True
        assert self.agent.validate_cio_range(24.0) is True

    def test_invalid_cio(self):
        assert self.agent.validate_cio_range(-25.0) is False
        assert self.agent.validate_cio_range(30.0) is False

    def test_valid_neighbor_list(self):
        neighbors = [f"CELL_{i}" for i in range(10)]
        assert self.agent.validate_neighbor_list(neighbors) is True

    def test_oversized_neighbor_list(self):
        neighbors = [f"CELL_{i}" for i in range(50)]
        assert self.agent.validate_neighbor_list(neighbors) is False
