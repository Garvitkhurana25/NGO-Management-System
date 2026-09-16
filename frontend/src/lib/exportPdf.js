// Client-side PDF export of a donor's full transaction history.
//
// Uses jsPDF + jspdf-autotable (both are npm deps) so the document is generated
// entirely in the browser — no server round trip, no CSRF, works offline once
// the bundle is loaded. Mildly branded with the "Warm Mission" palette.

import { jsPDF } from 'jspdf'
import autoTable from 'jspdf-autotable'
import { formatINR, formatDate, titleCase } from './format.js'

const BRAND = [27, 122, 99] // #1B7A63 forest green
const INK = [35, 41, 44]
const MUTED = [110, 118, 120]

export function exportDonationsPdf({ donorName, donations, totalGiven }) {
  const rows = (donations ?? []).map((d, i) => [
    String(i + 1),
    formatDate(d.date),
    d.campaign || '—',
    formatINR(d.amount),
    titleCase(d.status),
    d.receipt_number || '—',
  ])

  const doc = new jsPDF({ unit: 'pt', format: 'a4' })
  const W = doc.internal.pageSize.getWidth()
  const MARGIN = 40

  // Branded header bar
  doc.setFillColor(...BRAND)
  doc.rect(0, 0, W, 74, 'F')
  doc.setTextColor(255, 255, 255)
  doc.setFont('helvetica', 'bold')
  doc.setFontSize(18)
  doc.text('NGO Operations Platform', MARGIN, 30)
  doc.setFontSize(11)
  doc.setFont('helvetica', 'normal')
  doc.text(`Donation statement — ${donorName || 'Donor'}`, MARGIN, 50)
  doc.text(
    `Generated ${new Date().toLocaleString('en-IN', { day: '2-digit', month: 'short', year: 'numeric' })}`,
    MARGIN,
    66,
  )

  // Summary line under the bar
  const count = rows.length
  doc.setTextColor(...INK)
  doc.setFont('helvetica', 'bold')
  doc.setFontSize(11)
  doc.text(`${count} transaction${count === 1 ? '' : 's'}  ·  total ${formatINR(totalGiven)}`, MARGIN, 98)

  autoTable(doc, {
    startY: 112,
    margin: { left: MARGIN, right: MARGIN },
    head: [['#', 'Date', 'Campaign', 'Amount', 'Status', 'Receipt #']],
    body:
      rows.length > 0
        ? rows
        : [['—', '—', 'No donations on record yet.', '—', '—', '—']],
    styles: { font: 'helvetica', fontSize: 9, textColor: INK, cellPadding: 6 },
    headStyles: { fillColor: BRAND, textColor: 255, fontSize: 9, fontStyle: 'bold' },
    alternateRowStyles: { fillColor: [247, 245, 240] },
    columnStyles: {
      0: { cellWidth: 28 },
      3: { halign: 'right', fontStyle: 'bold' },
      4: { cellWidth: 90 },
    },
    didDrawPage: (data) => {
      doc.setFont('helvetica', 'normal')
      doc.setFontSize(8)
      doc.setTextColor(...MUTED)
      doc.text(
        `${donorName || 'Donor'} — ${formatINR(totalGiven)} total`,
        MARGIN,
        doc.internal.pageSize.getHeight() - 18,
      )
      doc.text(
        `Page ${data.pageNumber}`,
        doc.internal.pageSize.getWidth() - MARGIN,
        doc.internal.pageSize.getHeight() - 18,
        { align: 'right' },
      )
    },
  })

  const safe = (donorName || 'donor')
    .toLowerCase()
    .replace(/[^a-z0-9]+/g, '-')
    .replace(/^-+|-+$/g, '')
  doc.save(`donations-${safe || 'donor'}.pdf`)
}