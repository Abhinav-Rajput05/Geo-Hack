// Shared equirectangular projection for 1000x500 viewBox
// Used by both Page 1 WorldMap and Page 2 RiskHeatmap

export function projectPoint(lon: number, lat: number): [number, number] {
  const x = (lon + 180) * (1000 / 360);
  const y = (90 - lat) * (500 / 180);
  return [x, y];
}

// Key geographic coordinates (lat, lon)
export const GEO_COORDS: Record<string, { lat: number; lon: number }> = {
  India:        { lat: 20.5937,  lon: 78.9629 },
  China:        { lat: 35.8617,  lon: 104.1954 },
  Russia:       { lat: 61.5240,  lon: 105.3188 },
  USA:          { lat: 37.0902,  lon: -95.7129 },
  Brazil:       { lat: -14.2350, lon: -51.9253 },
  Nigeria:      { lat: 9.0820,   lon: 8.6753 },
  Iran:         { lat: 32.4279,  lon: 53.6880 },
  Germany:      { lat: 51.1657,  lon: 10.4515 },
  Australia:    { lat: -25.2744, lon: 133.7751 },
  Japan:        { lat: 36.2048,  lon: 138.2529 },
  UK:           { lat: 55.3781,  lon: -3.4360 },
  Turkey:       { lat: 38.9637,  lon: 35.2433 },
  Pakistan:     { lat: 30.3753,  lon: 69.3451 },
  SaudiArabia:  { lat: 23.8859,  lon: 45.0792 },
  SouthKorea:   { lat: 35.9078,  lon: 127.7669 },
  Israel:       { lat: 31.0461,  lon: 34.8516 },
  France:       { lat: 46.2276,  lon: 2.2137 },
  Ukraine:      { lat: 48.3794,  lon: 31.1656 },
};

// Connection endpoints from India to key regions (using real coords)
export const INDIA_PROJECTED = projectPoint(GEO_COORDS.India.lon, GEO_COORDS.India.lat);

export const CONNECTION_TARGETS = [
  { lon: 10.45,   lat: 51.17,  label: "Trade" },      // Germany/Europe
  { lon: 104.19,  lat: 35.86,  label: "Influence" },   // China/East Asia
  { lon: -95.71,  lat: 37.09,  label: "Conflict" },    // USA
  { lon: 53.69,   lat: 32.43,  label: "Energy" },      // Iran/Middle East
];
