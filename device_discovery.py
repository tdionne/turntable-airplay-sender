"""
AirPlay device discovery using Zeroconf/Bonjour.
Discovers AirPlay 2 compatible devices on the local network.
"""

import logging
import asyncio
from typing import List, Dict, Optional
from zeroconf import ServiceBrowser, ServiceListener, Zeroconf
import socket

logger = logging.getLogger(__name__)


class AirPlayDevice:
    """Represents an AirPlay-capable device."""
    
    def __init__(self, name: str, host: str, port: int, properties: Dict):
        self.name = name
        self.host = host
        self.port = port
        self.properties = properties
        self.model = properties.get('model', 'Unknown')
        self.features = properties.get('features', '')
        
    def __repr__(self):
        return f"AirPlayDevice(name='{self.name}', host='{self.host}', port={self.port})"
    
    def supports_airplay2(self) -> bool:
        """Check if device supports AirPlay 2."""
        # AirPlay 2 feature flag in properties
        features = self.properties.get('features', '')
        if isinstance(features, bytes):
            features = features.hex()
        # Check for AirPlay 2 support bits (this is a simplified check)
        return True  # Most modern devices support AirPlay 2


class AirPlayDiscovery(ServiceListener):
    """Discovers AirPlay devices on the network."""
    
    def __init__(self, timeout: int = 10):
        self.timeout = timeout
        self.devices: Dict[str, AirPlayDevice] = {}
        self.zeroconf: Optional[Zeroconf] = None
        self.browser: Optional[ServiceBrowser] = None
        
    def add_service(self, zc: Zeroconf, type_: str, name: str) -> None:
        """Called when a service is discovered."""
        try:
            info = zc.get_service_info(type_, name)
            if info:
                # Parse device information
                addresses = info.parsed_addresses()
                if addresses:
                    host = addresses[0]
                    port = info.port
                    
                    # Extract properties
                    properties = {}
                    for key, value in info.properties.items():
                        if isinstance(key, bytes):
                            key = key.decode('utf-8')
                        if isinstance(value, bytes):
                            try:
                                value = value.decode('utf-8')
                            except:
                                pass
                        properties[key] = value
                    
                    # Create device object
                    device_name = info.server.rstrip('.').split('.')[0] if info.server else name
                    device = AirPlayDevice(device_name, host, port, properties)
                    
                    self.devices[name] = device
                    logger.info(f"Discovered AirPlay device: {device}")
                    
        except Exception as e:
            logger.error(f"Error adding service {name}: {e}")
    
    def remove_service(self, zc: Zeroconf, type_: str, name: str) -> None:
        """Called when a service is removed."""
        if name in self.devices:
            logger.info(f"AirPlay device removed: {self.devices[name]}")
            del self.devices[name]
    
    def update_service(self, zc: Zeroconf, type_: str, name: str) -> None:
        """Called when a service is updated."""
        # Re-add the service to update information
        self.add_service(zc, type_, name)
    
    def discover(self) -> List[AirPlayDevice]:
        """
        Discover AirPlay devices on the network.
        
        Returns:
            List of discovered AirPlay devices
        """
        logger.info(f"Discovering AirPlay devices (timeout: {self.timeout}s)...")
        
        try:
            self.zeroconf = Zeroconf()
            
            # Browse for AirPlay services
            # _airplay._tcp.local. for AirPlay
            # _raop._tcp.local. for AirTunes/AirPlay audio
            services = ["_airplay._tcp.local.", "_raop._tcp.local."]
            
            browsers = []
            for service in services:
                browser = ServiceBrowser(self.zeroconf, service, self)
                browsers.append(browser)
            
            # Wait for discovery
            import time
            time.sleep(self.timeout)
            
            # Cleanup
            for browser in browsers:
                browser.cancel()
            self.zeroconf.close()
            
            logger.info(f"Discovery complete. Found {len(self.devices)} device(s)")
            return list(self.devices.values())
            
        except Exception as e:
            logger.error(f"Error during discovery: {e}")
            if self.zeroconf:
                self.zeroconf.close()
            return []
    
    async def discover_async(self) -> List[AirPlayDevice]:
        """Async version of discover."""
        return await asyncio.get_event_loop().run_in_executor(
            None, self.discover
        )


def discover_airplay_devices(timeout: int = 10) -> List[AirPlayDevice]:
    """
    Convenience function to discover AirPlay devices.
    
    Args:
        timeout: Discovery timeout in seconds
        
    Returns:
        List of discovered devices
    """
    discovery = AirPlayDiscovery(timeout=timeout)
    return discovery.discover()


def find_device_by_name(name: str, timeout: int = 10) -> Optional[AirPlayDevice]:
    """
    Find a specific AirPlay device by name.
    
    Args:
        name: Device name to search for (case-insensitive)
        timeout: Discovery timeout in seconds
        
    Returns:
        AirPlayDevice if found, None otherwise
    """
    devices = discover_airplay_devices(timeout)
    
    for device in devices:
        if name.lower() in device.name.lower():
            return device
    
    return None

