// Winner data. Spelling: "Al-Jufri" with hyphen per setkab.go.id; others exactly as supplied by the client.
export const WINNERS = {
  1: { cls: 'BANDAR UDARA KELAS I', name: 'UPBU MUTIARA SIS AL-JUFRI PALU', num: 'I' },
  2: { cls: 'BANDAR UDARA KELAS II', name: 'UPBU TAMPA PADANG MAMUJU', num: 'II' },
  3: { cls: 'BANDAR UDARA KELAS III / SATPEL', name: 'UPBU WAKATOBI', num: 'III' },
};
export const HEADER = ['LOMBA KEBERSIHAN DAN KERAPIHAN BANDAR UDARA', 'WILAYAH KERJA OTBAN V'];
export const pick = () => WINNERS[new URLSearchParams(location.search).get('k') || 1];
