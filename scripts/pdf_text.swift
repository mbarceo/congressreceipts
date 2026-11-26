// Prints the text of a PDF using macOS PDFKit. Used by build_trump_positions.py when `pdftotext` is not installed.
import PDFKit
import Foundation
for p in CommandLine.arguments.dropFirst() {
  if let d = PDFDocument(url: URL(fileURLWithPath: p)) { print(d.string ?? "") }
}
