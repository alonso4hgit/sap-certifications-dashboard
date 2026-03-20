// ============================================================
// SCRIPT PARA ACTUALIZAR DATOS DE SAP CERTIFICATIONS
// ============================================================
// INSTRUCCIONES:
// 1. Entra a https://me.sap.com/partner/dashboard/partnership/certifications
// 2. Abre la consola del navegador (F12 → Console)
// 3. Pega este código y presiona Enter
// 4. Se descargará sap_certifications.csv automáticamente
// 5. Copia el archivo a la carpeta /data/ del dashboard
// 6. Haz clic en "Recargar datos" en el dashboard
// ============================================================

(async () => {
  console.log('Extrayendo datos de SAP Certifications API...');

  const resp = await fetch('/backend/odata/partnergev/CertificationsV3', { credentials: 'include' });

  if (!resp.ok) {
    console.error('Error al llamar la API:', resp.status);
    alert('Error: No se pudo conectar a la API. Asegúrate de estar en la página de certificaciones.');
    return;
  }

  const data = await resp.json();
  const records = data.value;
  console.log(`✅ ${records.length} certificaciones encontradas`);

  const headers = [
    'partnerAccountId','partnerAccountName','certifiedUserName','certifiedUserEmail',
    'certificationId','certificationName','subSolutionAreaName','logicalProductName',
    'competencyName','authorizationDescription','dateIssued','dateExpiration','source','type'
  ];

  const rows = records.map(r => headers.map(h => `"${(r[h] || '').toString().replace(/"/g, '""')}"`).join(','));
  const csv = [headers.join(','), ...rows].join('\n');

  const blob = new Blob([csv], { type: 'text/csv;charset=utf-8;' });
  const a = document.createElement('a');
  a.href = URL.createObjectURL(blob);
  a.download = 'sap_certifications.csv';
  a.click();

  console.log('✅ Archivo descargado: sap_certifications.csv');
  alert(`✅ Listo! Se descargaron ${records.length} certificaciones.\n\nCopia sap_certifications.csv a la carpeta /data/ del dashboard.`);
})();
