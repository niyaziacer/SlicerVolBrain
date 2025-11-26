import os
import vtk
import qt
import ctk
import slicer
from slicer.ScriptedLoadableModule import *
from slicer.util import VTKObservationMixin
import numpy as np

class VolBrainVolumeCalculator(ScriptedLoadableModule):
    """3D Slicer modülü için temel sınıf."""
    
    def __init__(self, parent):
        ScriptedLoadableModule.__init__(self, parent)
        self.parent.title = "volBrain Hacim Hesaplayici"
        self.parent.categories = ["Quantification"]
        self.parent.dependencies = []
        self.parent.contributors = ["3D Slicer Kullanicisi"]
        self.parent.helpText = """volBrain segmentasyon sonuclarindan beyin yapi hacimlerini hesaplar ve 3D gorsellestirir."""
        self.parent.acknowledgementText = """volBrain tabanli hacim analizi modulu"""

class VolBrainVolumeCalculatorWidget(ScriptedLoadableModuleWidget, VTKObservationMixin):
    """Modulun kullanici arayuzu."""
    
    def __init__(self, parent=None):
        ScriptedLoadableModuleWidget.__init__(self, parent)
        VTKObservationMixin.__init__(self)
        self.logic = None
        self.volumeResults = {}
        self.loadedNodes = []
        self.currentSegmentationNode = None
        self.currentOpacity = 1.0
        
    def setup(self):
        """Arayuz bilesenlerini olusturur."""
        ScriptedLoadableModuleWidget.setup(self)
        
        self.logic = VolBrainVolumeCalculatorLogic()
        
        # Giris Dosyalari
        inputsCollapsibleButton = ctk.ctkCollapsibleButton()
        inputsCollapsibleButton.text = "Giris Dosyalari"
        self.layout.addWidget(inputsCollapsibleButton)
        inputsFormLayout = qt.QFormLayout(inputsCollapsibleButton)
        
        self.structuresSelector = ctk.ctkPathLineEdit()
        self.structuresSelector.filters = ctk.ctkPathLineEdit.Files
        self.structuresSelector.nameFilters = ["NIfTI (*.nii *.nii.gz)"]
        inputsFormLayout.addRow("Structures:", self.structuresSelector)
        
        self.tissuesSelector = ctk.ctkPathLineEdit()
        self.tissuesSelector.filters = ctk.ctkPathLineEdit.Files
        self.tissuesSelector.nameFilters = ["NIfTI (*.nii *.nii.gz)"]
        inputsFormLayout.addRow("Tissues:", self.tissuesSelector)
        
        self.lobesSelector = ctk.ctkPathLineEdit()
        self.lobesSelector.filters = ctk.ctkPathLineEdit.Files
        self.lobesSelector.nameFilters = ["NIfTI (*.nii *.nii.gz)"]
        inputsFormLayout.addRow("Lobes:", self.lobesSelector)
        
        self.macroSelector = ctk.ctkPathLineEdit()
        self.macroSelector.filters = ctk.ctkPathLineEdit.Files
        self.macroSelector.nameFilters = ["NIfTI (*.nii *.nii.gz)"]
        inputsFormLayout.addRow("Macrostructures:", self.macroSelector)
        
        self.quickLoadButton = qt.QPushButton("Klasorden Otomatik Yukle")
        inputsFormLayout.addRow(self.quickLoadButton)
        
        # Hesaplama
        calcCollapsibleButton = ctk.ctkCollapsibleButton()
        calcCollapsibleButton.text = "Hesaplama ve Gorsellestirme"
        self.layout.addWidget(calcCollapsibleButton)
        calcFormLayout = qt.QFormLayout(calcCollapsibleButton)
        
        self.progressBar = qt.QProgressBar()
        self.progressBar.setRange(0, 100)
        self.progressBar.setValue(0)
        calcFormLayout.addRow("Ilerleme:", self.progressBar)
        
        self.statusLabel = qt.QLabel("Hazir")
        calcFormLayout.addRow("Durum:", self.statusLabel)
        
        # 3D görselleştirme seçenekleri
        self.show3DCheckbox = qt.QCheckBox("3D Gorsellestirme")
        self.show3DCheckbox.checked = True
        calcFormLayout.addRow(self.show3DCheckbox)
        
        self.applyButton = qt.QPushButton("Hacimleri Hesapla ve Gorsellestir")
        self.applyButton.setStyleSheet("QPushButton { font-weight: bold; padding: 10px; }")
        calcFormLayout.addRow(self.applyButton)
        
        # Sonuclar
        resultsCollapsibleButton = ctk.ctkCollapsibleButton()
        resultsCollapsibleButton.text = "Sonuclar"
        resultsCollapsibleButton.collapsed = False
        self.layout.addWidget(resultsCollapsibleButton)
        resultsFormLayout = qt.QFormLayout(resultsCollapsibleButton)
        
        self.resultsTable = qt.QTableWidget()
        self.resultsTable.setColumnCount(5)
        self.resultsTable.setHorizontalHeaderLabels(["Kategori", "Label ID", "Yapi Adi", "Hacim (mm3)", "Hacim (ml)"])
        self.resultsTable.setColumnWidth(0, 120)
        self.resultsTable.setColumnWidth(1, 80)
        self.resultsTable.setColumnWidth(2, 250)
        self.resultsTable.setColumnWidth(3, 120)
        self.resultsTable.setColumnWidth(4, 100)
        self.resultsTable.setAlternatingRowColors(True)
        self.resultsTable.setSortingEnabled(True)
        self.resultsTable.setMinimumHeight(400)
        resultsFormLayout.addRow(self.resultsTable)
        
        self.summaryLabel = qt.QLabel("")
        self.summaryLabel.setWordWrap(True)
        resultsFormLayout.addRow("Ozet:", self.summaryLabel)
        
        # Export butonlari
        exportLayout = qt.QHBoxLayout()
        self.exportCSVButton = qt.QPushButton("💾 CSV")
        self.exportCSVButton.enabled = False
        self.exportCSVButton.setMaximumWidth(100)
        
        self.exportExcelButton = qt.QPushButton("📊 Excel")
        self.exportExcelButton.enabled = False
        self.exportExcelButton.setMaximumWidth(100)
        
        self.copyButton = qt.QPushButton("📋 Kopyala")
        self.copyButton.enabled = False
        self.copyButton.setMaximumWidth(100)
        
        self.clearButton = qt.QPushButton("🗑️ Temizle")
        self.clearButton.enabled = False
        self.clearButton.setMaximumWidth(100)
        
        exportLayout.addWidget(self.exportCSVButton)
        exportLayout.addWidget(self.exportExcelButton)
        exportLayout.addWidget(self.copyButton)
        exportLayout.addWidget(self.clearButton)
        exportLayout.addStretch()
        resultsFormLayout.addRow(exportLayout)
        
        # 3D Gorsellestime Kontrolleri
        visualCollapsibleButton = ctk.ctkCollapsibleButton()
        visualCollapsibleButton.text = "3D Gorsellestime Kontrolleri"
        visualCollapsibleButton.collapsed = True
        self.layout.addWidget(visualCollapsibleButton)
        visualFormLayout = qt.QFormLayout(visualCollapsibleButton)
        
        # Segment secimi
        self.segmentSelector = qt.QComboBox()
        self.segmentSelector.addItem("-- Tum Yapilar --")
        self.segmentSelector.enabled = False
        visualFormLayout.addRow("3D'de Goster:", self.segmentSelector)
        
        # Gorunurluk butonlari
        visibilityLayout = qt.QHBoxLayout()
        self.showAllButton = qt.QPushButton("👁️ Hepsini Goster")
        self.showAllButton.enabled = False
        self.hideAllButton = qt.QPushButton("🚫 Hepsini Gizle")
        self.hideAllButton.enabled = False
        self.toggleOpacityButton = qt.QPushButton("🌓 Saydamlik Degistir")
        self.toggleOpacityButton.enabled = False
        visibilityLayout.addWidget(self.showAllButton)
        visibilityLayout.addWidget(self.hideAllButton)
        visibilityLayout.addWidget(self.toggleOpacityButton)
        visualFormLayout.addRow(visibilityLayout)
        
        # Baglanti
        self.quickLoadButton.connect('clicked(bool)', self.onQuickLoad)
        self.applyButton.connect('clicked(bool)', self.onApplyButton)
        self.exportCSVButton.connect('clicked(bool)', self.onExportCSV)
        self.exportExcelButton.connect('clicked(bool)', self.onExportExcel)
        self.copyButton.connect('clicked(bool)', self.onCopyToClipboard)
        self.clearButton.connect('clicked(bool)', self.onClear)
        self.segmentSelector.connect('currentIndexChanged(int)', self.onSegmentSelected)
        self.showAllButton.connect('clicked(bool)', self.onShowAll)
        self.hideAllButton.connect('clicked(bool)', self.onHideAll)
        self.toggleOpacityButton.connect('clicked(bool)', self.onToggleOpacity)
        
        self.layout.addStretch(1)
        
    def cleanup(self):
        """Temizlik islemleri."""
        pass
    
    def onQuickLoad(self):
        """Klasorden otomatik dosya yukleme."""
        folder = qt.QFileDialog.getExistingDirectory(self.parent, "volBrain Sonuc Klasorunu Secin")
        
        if folder:
            files = os.listdir(folder)
            for f in files:
                fullPath = os.path.join(folder, f)
                if 'structures' in f.lower() and 'native' in f.lower() and not 'macro' in f.lower():
                    self.structuresSelector.setCurrentPath(fullPath)
                elif 'tissues' in f.lower() and 'native' in f.lower():
                    self.tissuesSelector.setCurrentPath(fullPath)
                elif 'lobes' in f.lower() and 'native' in f.lower():
                    self.lobesSelector.setCurrentPath(fullPath)
                elif 'macrostructures' in f.lower() and 'native' in f.lower():
                    self.macroSelector.setCurrentPath(fullPath)
            
            self.statusLabel.setText("Dosyalar otomatik yuklendi")
    
    def onApplyButton(self):
        """Hacim hesaplama islemini baslatir."""
        self.volumeResults = {}
        self.resultsTable.setRowCount(0)
        self.progressBar.setValue(0)
        self.statusLabel.setText("Hesaplama basliyor...")
        slicer.app.processEvents()
        
        # Dosya yollarini topla
        files = [
            (self.structuresSelector.currentPath, "structures"),
            (self.tissuesSelector.currentPath, "tissues"),
            (self.lobesSelector.currentPath, "lobes"),
            (self.macroSelector.currentPath, "macro")
        ]
        
        validFiles = [(path, cat) for path, cat in files if os.path.exists(path)]
        
        if not validFiles:
            slicer.util.errorDisplay("Lutfen en az bir dosya secin!")
            self.statusLabel.setText("Hata: Dosya secilmedi")
            return
        
        totalSteps = len(validFiles)
        currentStep = 0
        allResults = {}
        
        for filePath, category in validFiles:
            currentStep += 1
            self.progressBar.setValue(int(currentStep / totalSteps * 100))
            self.statusLabel.setText(f"{category} hesaplaniyor...")
            slicer.app.processEvents()
            
            try:
                results = self.logic.calculateVolumes(
                    filePath, 
                    category, 
                    show3D=self.show3DCheckbox.checked
                )
                allResults.update(results)
                
                # Node'u kaydet
                if self.show3DCheckbox.checked:
                    # Segmentation node'u bul ve kaydet
                    segNodeName = f"volBrain_{category}_Segmentation"
                    segNode = slicer.util.getFirstNodeByName(segNodeName)
                    if segNode:
                        self.loadedNodes.append(segNode)
                        if not self.currentSegmentationNode:
                            self.currentSegmentationNode = segNode
                
            except Exception as e:
                print(f"HATA {category}: {str(e)}")
                import traceback
                traceback.print_exc()
        
        self.volumeResults = allResults
        self.updateResultsTable()
        self.updateSummary()
        
        self.exportCSVButton.enabled = True
        self.exportExcelButton.enabled = True
        self.copyButton.enabled = True
        self.clearButton.enabled = True
        self.segmentSelector.enabled = True
        self.showAllButton.enabled = True
        self.hideAllButton.enabled = True
        self.toggleOpacityButton.enabled = True
        
        # Segment secici'yi doldur
        self.updateSegmentSelector()
        
        self.progressBar.setValue(100)
        self.statusLabel.setText(f"Tamamlandi! {len(allResults)} yapi hesaplandi")
        
        # 3D görünümü ayarla
        if self.show3DCheckbox.checked:
            layoutManager = slicer.app.layoutManager()
            layoutManager.setLayout(slicer.vtkMRMLLayoutNode.SlicerLayoutFourUpView)
            slicer.util.resetSliceViews()
        
        slicer.util.messageBox(f"Hacim hesaplamasi tamamlandi!\n\n{len(allResults)} beyin yapisi analiz edildi.")
    
    def updateResultsTable(self):
        """Sonuc tablosunu gunceller."""
        self.resultsTable.setRowCount(len(self.volumeResults))
        row = 0
        
        for structureKey, data in sorted(self.volumeResults.items()):
            self.resultsTable.setItem(row, 0, qt.QTableWidgetItem(data['category'].upper()))
            self.resultsTable.setItem(row, 1, qt.QTableWidgetItem(str(data['label_id'])))
            self.resultsTable.setItem(row, 2, qt.QTableWidgetItem(data['name']))
            self.resultsTable.setItem(row, 3, qt.QTableWidgetItem(f"{data['mm3']:.2f}"))
            self.resultsTable.setItem(row, 4, qt.QTableWidgetItem(f"{data['ml']:.4f}"))
            row += 1
    
    def updateSummary(self):
        """Ozet istatistikleri gunceller."""
        if not self.volumeResults:
            return
        
        categories = {}
        for data in self.volumeResults.values():
            cat = data['category']
            if cat not in categories:
                categories[cat] = {'count': 0, 'total_ml': 0}
            categories[cat]['count'] += 1
            categories[cat]['total_ml'] += data['ml']
        
        summary = "<b>Kategori Ozeti:</b><br>"
        for cat, stats in sorted(categories.items()):
            summary += f"{cat.upper()}: {stats['count']} yapi, Toplam: {stats['total_ml']:.2f} ml<br>"
        
        self.summaryLabel.setText(summary)
    
    def onExportCSV(self):
        """CSV formatinda disa aktarim."""
        fileName = qt.QFileDialog.getSaveFileName(
            self.parent, "CSV Dosyasini Kaydet", 
            os.path.expanduser("~/volbrain_volumes.csv"), 
            "CSV Files (*.csv)")
        
        if fileName:
            try:
                with open(fileName, 'w', encoding='utf-8') as f:
                    f.write("Kategori,Label_ID,Yapi_Adi,Hacim_mm3,Hacim_ml\n")
                    for data in sorted(self.volumeResults.values(), key=lambda x: (x['category'], x['label_id'])):
                        f.write(f"{data['category']},{data['label_id']},{data['name']},{data['mm3']:.2f},{data['ml']:.4f}\n")
                
                slicer.util.messageBox(f"Sonuclar kaydedildi:\n{fileName}")
                self.statusLabel.setText("CSV kaydedildi")
            except Exception as e:
                slicer.util.errorDisplay(f"Kaydetme hatasi: {str(e)}")
    
    def onCopyToClipboard(self):
        """Sonuclari panoya kopyala."""
        text = "Kategori\tLabel_ID\tYapi_Adi\tHacim_mm3\tHacim_ml\n"
        for data in sorted(self.volumeResults.values(), key=lambda x: (x['category'], x['label_id'])):
            text += f"{data['category']}\t{data['label_id']}\t{data['name']}\t{data['mm3']:.2f}\t{data['ml']:.4f}\n"
        
        clipboard = qt.QApplication.clipboard()
        clipboard.setText(text)
        self.statusLabel.setText("Panoya kopyalandi")
        slicer.util.messageBox("Sonuclar panoya kopyalandi!")
    
    def onClear(self):
        """Yuklenen node'lari temizle."""
        for node in self.loadedNodes:
            slicer.mrmlScene.RemoveNode(node)
        self.loadedNodes = []
        self.currentSegmentationNode = None
        self.segmentSelector.clear()
        self.segmentSelector.addItem("-- Tum Yapilar --")
        self.segmentSelector.enabled = False
        self.showAllButton.enabled = False
        self.hideAllButton.enabled = False
        self.toggleOpacityButton.enabled = False
        self.statusLabel.setText("Temizlendi")
    
    def updateSegmentSelector(self):
        """Segment secici'yi guncelle."""
        self.segmentSelector.clear()
        self.segmentSelector.addItem("-- Tum Yapilar --")
        
        # Tum segmentation node'lari bul
        for node in self.loadedNodes:
            if node.IsA('vtkMRMLSegmentationNode'):
                self.currentSegmentationNode = node
                segmentation = node.GetSegmentation()
                for i in range(segmentation.GetNumberOfSegments()):
                    segmentId = segmentation.GetNthSegmentID(i)
                    segment = segmentation.GetSegment(segmentId)
                    self.segmentSelector.addItem(segment.GetName(), segmentId)
    
    def onSegmentSelected(self, index):
        """Secilen segment'i 3D'de goster."""
        if not self.currentSegmentationNode:
            return
        
        segmentation = self.currentSegmentationNode.GetSegmentation()
        displayNode = self.currentSegmentationNode.GetDisplayNode()
        
        if index == 0:  # "Tum Yapilar" secildi
            # Hepsini goster
            for i in range(segmentation.GetNumberOfSegments()):
                segmentId = segmentation.GetNthSegmentID(i)
                displayNode.SetSegmentVisibility3D(segmentId, True)
        else:
            # Sadece secileni goster
            selectedSegmentId = self.segmentSelector.itemData(index)
            for i in range(segmentation.GetNumberOfSegments()):
                segmentId = segmentation.GetNthSegmentID(i)
                if segmentId == selectedSegmentId:
                    displayNode.SetSegmentVisibility3D(segmentId, True)
                else:
                    displayNode.SetSegmentVisibility3D(segmentId, False)
    
    def onShowAll(self):
        """Tum segmentleri goster."""
        if not self.currentSegmentationNode:
            return
        
        segmentation = self.currentSegmentationNode.GetSegmentation()
        displayNode = self.currentSegmentationNode.GetDisplayNode()
        
        for i in range(segmentation.GetNumberOfSegments()):
            segmentId = segmentation.GetNthSegmentID(i)
            displayNode.SetSegmentVisibility3D(segmentId, True)
        
        self.segmentSelector.setCurrentIndex(0)
        self.statusLabel.setText("Tum yapilar gosteriliyor")
    
    def onHideAll(self):
        """Tum segmentleri gizle."""
        if not self.currentSegmentationNode:
            return
        
        segmentation = self.currentSegmentationNode.GetSegmentation()
        displayNode = self.currentSegmentationNode.GetDisplayNode()
        
        for i in range(segmentation.GetNumberOfSegments()):
            segmentId = segmentation.GetNthSegmentID(i)
            displayNode.SetSegmentVisibility3D(segmentId, False)
        
        self.statusLabel.setText("Tum yapilar gizlendi")
    
    def onToggleOpacity(self):
        """3D gorunum saydamligini degistir."""
        if not self.currentSegmentationNode:
            return
        
        displayNode = self.currentSegmentationNode.GetDisplayNode()
        
        # Opacity'yi degistir: 1.0 -> 0.5 -> 0.2 -> 1.0
        if self.currentOpacity >= 1.0:
            self.currentOpacity = 0.5
        elif self.currentOpacity >= 0.5:
            self.currentOpacity = 0.2
        else:
            self.currentOpacity = 1.0
        
        displayNode.SetOpacity3D(self.currentOpacity)
        self.statusLabel.setText(f"Saydamlik: {int(self.currentOpacity*100)}%")
    
    def onExportExcel(self):
        """Excel formatinda disa aktarim."""
        fileName = qt.QFileDialog.getSaveFileName(
            self.parent, "Excel Dosyasini Kaydet", 
            os.path.expanduser("~/volbrain_volumes.csv"), 
            "CSV Files (*.csv)")
        
        if fileName:
            try:
                # Excel icin tab-delimited CSV
                with open(fileName, 'w', encoding='utf-8-sig') as f:  # BOM ekle Excel icin
                    f.write("Kategori\tLabel_ID\tYapi_Adi\tHacim_mm3\tHacim_ml\n")
                    for data in sorted(self.volumeResults.values(), key=lambda x: (x['category'], x['label_id'])):
                        f.write(f"{data['category']}\t{data['label_id']}\t{data['name']}\t{data['mm3']:.2f}\t{data['ml']:.4f}\n")
                
                slicer.util.messageBox(f"Excel dosyasi kaydedildi:\n{fileName}\n\nExcel'de acmak icin:\n1. Excel'i acin\n2. Dosya > Ac\n3. 'Tum Dosyalar' secin\n4. CSV dosyasini secin")
                self.statusLabel.setText("Excel dosyasi kaydedildi")
            except Exception as e:
                slicer.util.errorDisplay(f"Kaydetme hatasi: {str(e)}")

class VolBrainVolumeCalculatorLogic(ScriptedLoadableModuleLogic):
    """Hacim hesaplama mantigi."""
    
    def __init__(self):
        ScriptedLoadableModuleLogic.__init__(self)
    
    def calculateVolumes(self, filePath, category, show3D=True):
        """Belirtilen dosyadan hacim hesaplar."""
        
        nodeName = f"volBrain_{category}"
        
        # Eski node varsa sil
        try:
            oldNode = slicer.util.getNode(nodeName)
            if oldNode:
                slicer.mrmlScene.RemoveNode(oldNode)
        except:
            pass  # Node yoksa sorun yok
        
        # NIfTI dosyasini yukle
        volumeNode = slicer.util.loadVolume(filePath, returnNode=True)[1]
        volumeNode.SetName(nodeName)
        
        # Voxel boyutlarini al
        spacing = volumeNode.GetSpacing()
        voxelVolume = spacing[0] * spacing[1] * spacing[2]
        
        # Label haritasina donustur
        labelNode = slicer.mrmlScene.AddNewNodeByClass('vtkMRMLLabelMapVolumeNode')
        labelNode.SetName(f"{nodeName}_labels")
        slicer.modules.volumes.logic().CreateLabelVolumeFromVolume(slicer.mrmlScene, labelNode, volumeNode)
        
        # Array'i al
        array = slicer.util.arrayFromVolume(labelNode)
        uniqueLabels = np.unique(array)
        uniqueLabels = uniqueLabels[uniqueLabels > 0]
        
        results = {}
        labelNames = self.getLabelNames(category)
        colorTable = self.getColorTable(category)
        
        # Renk tablosu olustur
        colorNode = slicer.mrmlScene.CreateNodeByClass('vtkMRMLColorTableNode')
        colorNode.SetName(f"{nodeName}_ColorTable")
        colorNode.SetTypeToUser()
        colorNode.SetNumberOfColors(int(np.max(uniqueLabels)) + 1)
        colorNode.NamesInitialisedOn()
        
        # Arka plan
        colorNode.SetColor(0, "Background", 0.0, 0.0, 0.0, 0.0)
        
        for label in uniqueLabels:
            labelInt = int(label)
            voxelCount = np.sum(array == label)
            volumeMm3 = float(voxelCount * voxelVolume)
            volumeMl = volumeMm3 / 1000.0
            
            labelName = labelNames.get(labelInt, f"Label_{labelInt}")
            structureKey = f"{category}_{labelInt}_{labelName}"
            
            results[structureKey] = {
                "category": category,
                "label_id": labelInt,
                "name": labelName,
                "mm3": volumeMm3, 
                "ml": volumeMl
            }
            
            # Renk ata
            if labelInt in colorTable:
                r, g, b = colorTable[labelInt]
                colorNode.SetColor(labelInt, labelName, r, g, b, 1.0)
            else:
                # Rastgele renk
                import random
                r, g, b = random.random(), random.random(), random.random()
                colorNode.SetColor(labelInt, labelName, r, g, b, 1.0)
        
        slicer.mrmlScene.AddNode(colorNode)
        
        # Label node'a renk tablosunu ata
        displayNode = labelNode.GetDisplayNode()
        if not displayNode:
            displayNode = slicer.mrmlScene.CreateNodeByClass('vtkMRMLLabelMapVolumeDisplayNode')
            slicer.mrmlScene.AddNode(displayNode)
            labelNode.SetAndObserveDisplayNodeID(displayNode.GetID())
        
        displayNode.SetAndObserveColorNodeID(colorNode.GetID())
        
        # 3D gorsellestirme
        if show3D:
            # Segmentation olustur
            segmentationNode = slicer.mrmlScene.AddNewNodeByClass('vtkMRMLSegmentationNode')
            segmentationNode.SetName(f"{nodeName}_Segmentation")
            
            # Label map'i segmentasyona cevir
            slicer.modules.segmentations.logic().ImportLabelmapToSegmentationNode(labelNode, segmentationNode)
            
            # Her segment icin isim ata
            segmentation = segmentationNode.GetSegmentation()
            for labelInt in uniqueLabels:
                labelName = labelNames.get(int(labelInt), f"Label_{int(labelInt)}")
                segmentId = segmentation.GetSegmentIdBySegmentName(f"Label_{int(labelInt)}")
                if segmentId:
                    segment = segmentation.GetSegment(segmentId)
                    segment.SetName(labelName)
                    
                    # Renk ata
                    if int(labelInt) in colorTable:
                        r, g, b = colorTable[int(labelInt)]
                        segment.SetColor(r, g, b)
            
            # 3D gosterimi aktif et
            segmentationNode.CreateClosedSurfaceRepresentation()
            displayNode = segmentationNode.GetDisplayNode()
            if displayNode:
                displayNode.SetVisibility3D(True)
                displayNode.SetVisibility2DFill(True)
                displayNode.SetVisibility2DOutline(True)
        
        # Orjinal volume node'u sil
        slicer.mrmlScene.RemoveNode(volumeNode)
        
        return results
    
    def getLabelNames(self, category):
        """volBrain etiket isimlendirmelerini dondurur - README.pdf'e gore."""
        labels = {}
        
        if category == "structures":
            # README.pdf'deki native_structures etiketleri
            labels = {
                4: "3rd_Ventricle", 11: "4th_Ventricle",
                23: "Right_Accumbens", 30: "Left_Accumbens",
                31: "Right_Amygdala", 32: "Left_Amygdala",
                35: "Brainstem",
                36: "Right_Caudate", 37: "Left_Caudate",
                38: "Right_Cerebellum_Exterior", 39: "Left_Cerebellum_Exterior",
                40: "Right_Cerebellum_White_Matter", 41: "Left_Cerebellum_White_Matter",
                44: "Right_Cerebral_White_Matter", 45: "Left_Cerebral_White_Matter",
                47: "Right_Hippocampus", 48: "Left_Hippocampus",
                49: "Right_Inf_Lat_Vent", 50: "Left_Inf_Lat_Vent",
                51: "Right_Lateral_Ventricle", 52: "Left_Lateral_Ventricle",
                55: "Right_Pallidum", 56: "Left_Pallidum",
                57: "Right_Putamen", 58: "Left_Putamen",
                59: "Right_Thalamus", 60: "Left_Thalamus",
                61: "Right_Ventral_DC", 62: "Left_Ventral_DC",
                71: "Lobules_I-V", 72: "Lobules_VI-VII", 73: "Lobules_VIII-X",
                75: "Left_Basal_Forebrain", 76: "Right_Basal_Forebrain",
                # Kortikal yapilar (100-207)
                100: "R_anterior_cingulate", 101: "L_anterior_cingulate",
                102: "R_anterior_insula", 103: "L_anterior_insula",
                104: "R_anterior_orbital", 105: "L_anterior_orbital",
                106: "R_angular_gyrus", 107: "L_angular_gyrus",
                108: "R_calcarine_cortex", 109: "L_calcarine_cortex",
                112: "R_central_operculum", 113: "L_central_operculum",
                114: "R_cuneus", 115: "L_cuneus",
                116: "R_entorhinal", 117: "L_entorhinal",
                118: "R_frontal_operculum", 119: "L_frontal_operculum",
                120: "R_frontal_pole", 121: "L_frontal_pole",
                122: "R_fusiform_gyrus", 123: "L_fusiform_gyrus",
                124: "R_gyrus_rectus", 125: "L_gyrus_rectus",
                128: "R_inf_occipital", 129: "L_inf_occipital",
                132: "R_inf_temporal", 133: "L_inf_temporal",
                134: "R_lingual_gyrus", 135: "L_lingual_gyrus",
                136: "R_lateral_orbital", 137: "L_lateral_orbital",
                138: "R_middle_cingulate", 139: "L_middle_cingulate",
                140: "R_medial_frontal", 141: "L_medial_frontal",
                142: "R_middle_frontal", 143: "L_middle_frontal",
                144: "R_middle_occipital", 145: "L_middle_occipital",
                146: "R_medial_orbital", 147: "L_medial_orbital",
                148: "R_postcentral_medial", 149: "L_postcentral_medial",
                150: "R_precentral_medial", 151: "L_precentral_medial",
                152: "R_sup_frontal_medial", 153: "L_sup_frontal_medial",
                154: "R_middle_temporal", 155: "L_middle_temporal",
                156: "R_occipital_pole", 157: "L_occipital_pole",
                160: "R_occipital_fusiform", 161: "L_occipital_fusiform",
                162: "R_opercular_inf_frontal", 163: "L_opercular_inf_frontal",
                164: "R_orbital_inf_frontal", 165: "L_orbital_inf_frontal",
                166: "R_posterior_cingulate", 167: "L_posterior_cingulate",
                168: "R_precuneus", 169: "L_precuneus",
                170: "R_parahippocampal", 171: "L_parahippocampal",
                172: "R_posterior_insula", 173: "L_posterior_insula",
                174: "R_parietal_operculum", 175: "L_parietal_operculum",
                176: "R_postcentral_gyrus", 177: "L_postcentral_gyrus",
                178: "R_posterior_orbital", 179: "L_posterior_orbital",
                180: "R_planum_polare", 181: "L_planum_polare",
                182: "R_precentral_gyrus", 183: "L_precentral_gyrus",
                184: "R_planum_temporale", 185: "L_planum_temporale",
                186: "R_subcallosal", 187: "L_subcallosal",
                190: "R_sup_frontal", 191: "L_sup_frontal",
                192: "R_supplementary_motor", 193: "L_supplementary_motor",
                194: "R_supramarginal", 195: "L_supramarginal",
                196: "R_sup_occipital", 197: "L_sup_occipital",
                198: "R_sup_parietal_lobule", 199: "L_sup_parietal_lobule",
                200: "R_sup_temporal", 201: "L_sup_temporal",
                202: "R_temporal_pole", 203: "L_temporal_pole",
                204: "R_triangular_inf_frontal", 205: "L_triangular_inf_frontal",
                206: "R_transverse_temporal", 207: "L_transverse_temporal"
            }
        elif category == "tissues":
            # README.pdf'deki native_tissues etiketleri
            labels = {
                1: "CSF",
                2: "Cortical_GM",
                3: "Cerebrum_WM",
                4: "Subcortical_GM",
                5: "Cerebellum_GM",
                6: "Cerebellum_WM",
                7: "Brainstem"
            }
        elif category == "lobes":
            # README.pdf'deki native_lobes etiketleri
            labels = {
                1: "Right_Frontal_Lobe",
                2: "Left_Frontal_Lobe",
                3: "Right_Temporal_Lobe",
                4: "Left_Temporal_Lobe",
                5: "Right_Parietal_Lobe",
                6: "Left_Parietal_Lobe",
                7: "Right_Occipital_Lobe",
                8: "Left_Occipital_Lobe",
                9: "Right_Limbic_Lobe",
                10: "Left_Limbic_Lobe",
                11: "Right_Insular_Lobe",
                12: "Left_Insular_Lobe"
            }
        elif category == "macro":
            # README.pdf'deki native_macrostructures etiketleri
            labels = {
                1: "Left_Cerebrum",
                2: "Right_Cerebrum",
                3: "Left_Cerebellum",
                4: "Right_Cerebellum",
                5: "Vermal",
                6: "Brainstem"
            }
        
        return labels
    
    def getColorTable(self, category):
        """Her kategori icin renk tablosu - README.pdf'e gore."""
        colors = {}
        
        if category == "structures":
            # Ventrikuller - Mavi tonlari
            colors[4] = (0.2, 0.4, 0.9)   # 3rd Ventricle
            colors[11] = (0.3, 0.5, 0.95)  # 4th Ventricle
            colors[49] = (0.25, 0.45, 0.85) # Right Inf Lat Vent
            colors[50] = (0.35, 0.55, 0.9)  # Left Inf Lat Vent
            colors[51] = (0.2, 0.5, 1.0)    # Right Lateral Ventricle
            colors[52] = (0.3, 0.6, 1.0)    # Left Lateral Ventricle
            
            # Accumbens - Pembe
            colors[23] = (0.9, 0.3, 0.5)
            colors[30] = (0.95, 0.35, 0.55)
            
            # Amygdala - Kirmizi
            colors[31] = (0.8, 0.2, 0.2)
            colors[32] = (0.85, 0.25, 0.25)
            
            # Brainstem - Gri
            colors[35] = (0.5, 0.5, 0.5)
            
            # Caudate - Acik yesil
            colors[36] = (0.3, 0.7, 0.4)
            colors[37] = (0.35, 0.75, 0.45)
            
            # Cerebellum Exterior - Turuncu
            colors[38] = (0.9, 0.6, 0.3)
            colors[39] = (0.95, 0.65, 0.35)
            
            # Cerebellum WM - Kahverengi
            colors[40] = (0.7, 0.5, 0.3)
            colors[41] = (0.75, 0.55, 0.35)
            
            # Cerebral WM - Beyaz/Acik gri
            colors[44] = (0.9, 0.9, 0.9)
            colors[45] = (0.85, 0.85, 0.85)
            
            # Hippocampus - Sari
            colors[47] = (0.9, 0.8, 0.2)
            colors[48] = (0.95, 0.85, 0.25)
            
            # Pallidum - Koyu yesil
            colors[55] = (0.4, 0.6, 0.3)
            colors[56] = (0.45, 0.65, 0.35)
            
            # Putamen - Yesil
            colors[57] = (0.3, 0.8, 0.4)
            colors[58] = (0.35, 0.85, 0.45)
            
            # Thalamus - Mor
            colors[59] = (0.6, 0.2, 0.6)
            colors[60] = (0.65, 0.25, 0.65)
            
            # Ventral DC - Acik mor
            colors[61] = (0.7, 0.4, 0.7)
            colors[62] = (0.75, 0.45, 0.75)
            
            # Cerebellum Lobules - Turuncu tonlari
            colors[71] = (0.85, 0.5, 0.2)
            colors[72] = (0.9, 0.55, 0.25)
            colors[73] = (0.95, 0.6, 0.3)
            
            # Basal Forebrain - Acik pembe
            colors[75] = (0.8, 0.5, 0.6)
            colors[76] = (0.85, 0.55, 0.65)
            
            # Kortikal yapilar (100-207) - Spektrum renkleri
            # Frontal - Kirmizi tonlari
            for label in [100, 101, 104, 105, 118, 119, 120, 121, 124, 125, 136, 137, 
                         140, 141, 142, 143, 146, 147, 150, 151, 152, 153, 162, 163, 
                         164, 165, 178, 179, 182, 183, 186, 187, 190, 191, 192, 193, 
                         204, 205]:
                if label % 2 == 0:
                    colors[label] = (0.8, 0.2, 0.2)
                else:
                    colors[label] = (0.85, 0.25, 0.25)
            
            # Temporal - Mavi tonlari
            for label in [122, 123, 132, 133, 154, 155, 180, 181, 184, 185, 200, 201, 
                         202, 203, 206, 207]:
                if label % 2 == 0:
                    colors[label] = (0.2, 0.2, 0.8)
                else:
                    colors[label] = (0.25, 0.25, 0.85)
            
            # Parietal - Yesil tonlari
            for label in [106, 107, 148, 149, 168, 169, 174, 175, 176, 177, 194, 195, 
                         198, 199]:
                if label % 2 == 0:
                    colors[label] = (0.2, 0.7, 0.3)
                else:
                    colors[label] = (0.25, 0.75, 0.35)
            
            # Occipital - Sari tonlari
            for label in [108, 109, 114, 115, 128, 129, 134, 135, 144, 145, 156, 157, 
                         160, 161, 196, 197]:
                if label % 2 == 0:
                    colors[label] = (0.9, 0.8, 0.2)
                else:
                    colors[label] = (0.95, 0.85, 0.25)
            
            # Cingulate - Mor tonlari
            for label in [138, 139, 166, 167]:
                if label % 2 == 0:
                    colors[label] = (0.6, 0.2, 0.6)
                else:
                    colors[label] = (0.65, 0.25, 0.65)
            
            # Insula - Turuncu
            for label in [102, 103, 172, 173]:
                if label % 2 == 0:
                    colors[label] = (0.9, 0.5, 0.2)
                else:
                    colors[label] = (0.95, 0.55, 0.25)
            
            # Parahippocampal/Entorhinal - Acik sari
            for label in [116, 117, 170, 171]:
                if label % 2 == 0:
                    colors[label] = (0.8, 0.7, 0.3)
                else:
                    colors[label] = (0.85, 0.75, 0.35)
            
            # Central operculum - Pembe
            for label in [112, 113]:
                if label % 2 == 0:
                    colors[label] = (0.9, 0.4, 0.5)
                else:
                    colors[label] = (0.95, 0.45, 0.55)
                    
        elif category == "tissues":
            colors[1] = (0.3, 0.6, 0.9)   # CSF - Mavi
            colors[2] = (0.7, 0.7, 0.7)   # Cortical GM - Gri
            colors[3] = (0.9, 0.9, 0.9)   # Cerebrum WM - Beyaz
            colors[4] = (0.5, 0.7, 0.4)   # Subcortical GM - Yesil
            colors[5] = (0.9, 0.6, 0.3)   # Cerebellum GM - Turuncu
            colors[6] = (0.8, 0.5, 0.2)   # Cerebellum WM - Kahverengi
            colors[7] = (0.5, 0.5, 0.5)   # Brainstem - Gri
            
        elif category == "lobes":
            colors[1] = (0.9, 0.3, 0.3)   # Right Frontal - Kirmizi
            colors[2] = (0.95, 0.35, 0.35) # Left Frontal
            colors[3] = (0.3, 0.3, 0.9)   # Right Temporal - Mavi
            colors[4] = (0.35, 0.35, 0.95) # Left Temporal
            colors[5] = (0.3, 0.8, 0.3)   # Right Parietal - Yesil
            colors[6] = (0.35, 0.85, 0.35) # Left Parietal
            colors[7] = (0.9, 0.9, 0.3)   # Right Occipital - Sari
            colors[8] = (0.95, 0.95, 0.35) # Left Occipital
            colors[9] = (0.7, 0.3, 0.7)   # Right Limbic - Mor
            colors[10] = (0.75, 0.35, 0.75) # Left Limbic
            colors[11] = (0.9, 0.5, 0.3)  # Right Insular - Turuncu
            colors[12] = (0.95, 0.55, 0.35) # Left Insular
            
        elif category == "macro":
            colors[1] = (0.8, 0.7, 0.7)   # Left Cerebrum - Acik gri
            colors[2] = (0.75, 0.65, 0.65) # Right Cerebrum
            colors[3] = (0.9, 0.6, 0.3)   # Left Cerebellum - Turuncu
            colors[4] = (0.85, 0.55, 0.25) # Right Cerebellum
            colors[5] = (0.95, 0.65, 0.35) # Vermal - Acik turuncu
            colors[6] = (0.5, 0.5, 0.5)   # Brainstem - Gri
        
        return colors

class VolBrainVolumeCalculatorTest(ScriptedLoadableModuleTest):
    """Test sinifi."""
    
    def setUp(self):
        slicer.mrmlScene.Clear()
    
    def runTest(self):
        self.setUp()
        self.test_VolBrainVolumeCalculator1()
    
    def test_VolBrainVolumeCalculator1(self):
        self.delayDisplay("Test basliyor")
        self.delayDisplay('Test tamamlandi')