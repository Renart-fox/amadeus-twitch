import yaml

class Amadeus_Config():
    def __init__(self, config_path: str) -> None:
        with open(config_path, 'r') as f:
            config = yaml.safe_load(f)
        
        self.obs_host = config['obs']['host']
        self.obs_port = config['obs']['port']
        self.obs_password = config['obs']['password']
    
    def __repr__(self) -> str:
        return f"Amadeus_Config(obs_host={self.obs_host}, obs_port={self.obs_port}, obs_password={self.obs_password})"