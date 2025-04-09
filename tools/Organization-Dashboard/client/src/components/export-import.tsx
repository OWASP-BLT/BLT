import React, { useState } from 'react';
import { Button } from '@/components/ui/button';
import { Dialog, DialogContent, DialogDescription, DialogFooter, DialogHeader, DialogTitle, DialogTrigger } from '@/components/ui/dialog';
import { Label } from '@/components/ui/label';
import { useToast } from '@/hooks/use-toast';
import { DownloadIcon, UploadIcon } from 'lucide-react';
import { Input } from '@/components/ui/input';
import { Tabs, TabsContent, TabsList, TabsTrigger } from '@/components/ui/tabs';
import axios from 'axios';

type EntityType = 'bugs' | 'security-issues' | 'users' | 'activity';

interface ExportImportProps {
  entityType: EntityType;
  onImportComplete?: () => void;
}

export function ExportImport({ entityType, onImportComplete }: ExportImportProps) {
  const [file, setFile] = useState<File | null>(null);
  const [importError, setImportError] = useState('');
  const [isExporting, setIsExporting] = useState(false);
  const [isImporting, setIsImporting] = useState(false);
  const { toast } = useToast();

  const handleExport = async () => {
    try {
      setIsExporting(true);
      const response = await axios.get(`/api/export/${entityType}`);
      
      // Create and download the file
      const blob = new Blob([JSON.stringify(response.data, null, 2)], { type: 'application/json' });
      const url = URL.createObjectURL(blob);
      const a = document.createElement('a');
      a.href = url;
      a.download = `${entityType}-export-${new Date().toISOString().split('T')[0]}.json`;
      document.body.appendChild(a);
      a.click();
      document.body.removeChild(a);
      URL.revokeObjectURL(url);
      
      toast({
        title: 'Export Successful',
        description: `${entityType} data exported successfully`,
      });
    } catch (error) {
      console.error('Export error:', error);
      toast({
        title: 'Export Failed',
        description: 'There was an error exporting the data. Please try again.',
        variant: 'destructive',
      });
    } finally {
      setIsExporting(false);
    }
  };

  const handleFileChange = (e: React.ChangeEvent<HTMLInputElement>) => {
    if (e.target.files && e.target.files.length > 0) {
      setFile(e.target.files[0]);
      setImportError('');
    }
  };

  const handleImport = async () => {
    if (!file) {
      setImportError('Please select a file to import');
      return;
    }

    try {
      setIsImporting(true);
      
      const reader = new FileReader();
      reader.onload = async (event) => {
        if (event.target?.result) {
          try {
            const fileContent = JSON.parse(event.target.result as string);
            
            // Send the data to the server
            await axios.post(`/api/import/${entityType}`, fileContent, {
              headers: {
                'Content-Type': 'application/json',
              },
            });
            
            toast({
              title: 'Import Successful',
              description: `${entityType} data imported successfully`,
            });
            
            if (onImportComplete) {
              onImportComplete();
            }
            
            // Reset form
            setFile(null);
            if (document.getElementById('import-file') as HTMLInputElement) {
              (document.getElementById('import-file') as HTMLInputElement).value = '';
            }
          } catch (error) {
            console.error('JSON parsing error:', error);
            setImportError('Invalid JSON format in the imported file');
          }
        }
      };
      
      reader.onerror = () => {
        setImportError('Error reading file');
      };
      
      reader.readAsText(file);
    } catch (error) {
      console.error('Import error:', error);
      toast({
        title: 'Import Failed',
        description: 'There was an error importing the data. Please try again.',
        variant: 'destructive',
      });
    } finally {
      setIsImporting(false);
    }
  };

  const getEntityName = (type: EntityType): string => {
    switch (type) {
      case 'bugs':
        return 'Bug Reports';
      case 'security-issues':
        return 'Security Issues';
      case 'users':
        return 'Users';
      case 'activity':
        return 'Activity Logs';
      default:
        return 'Data';
    }
  };

  return (
    <Dialog>
      <DialogTrigger asChild>
        <Button variant="outline" className="flex items-center gap-2">
          <DownloadIcon className="h-4 w-4" />
          <span>Export/Import</span>
        </Button>
      </DialogTrigger>
      <DialogContent className="sm:max-w-[500px]">
        <DialogHeader>
          <DialogTitle>Export or Import {getEntityName(entityType)}</DialogTitle>
          <DialogDescription>
            Export data to a JSON file or import data from a previously exported file.
          </DialogDescription>
        </DialogHeader>
        
        <Tabs defaultValue="export" className="mt-4">
          <TabsList className="grid w-full grid-cols-2">
            <TabsTrigger value="export">Export</TabsTrigger>
            <TabsTrigger value="import">Import</TabsTrigger>
          </TabsList>
          
          <TabsContent value="export" className="mt-4">
            <div className="space-y-4">
              <p className="text-sm text-gray-500">
                Export your {getEntityName(entityType).toLowerCase()} to a JSON file that you can backup or share.
              </p>
              <Button 
                onClick={handleExport} 
                className="w-full" 
                disabled={isExporting}
              >
                {isExporting ? 'Exporting...' : 'Export to JSON'}
              </Button>
            </div>
          </TabsContent>
          
          <TabsContent value="import" className="mt-4">
            <div className="space-y-4">
              <p className="text-sm text-gray-500">
                Import {getEntityName(entityType).toLowerCase()} from a previously exported JSON file.
              </p>
              
              <div className="grid w-full items-center gap-1.5">
                <Label htmlFor="import-file">Select File</Label>
                <Input 
                  id="import-file" 
                  type="file" 
                  accept=".json" 
                  onChange={handleFileChange} 
                />
                {importError && (
                  <p className="text-sm text-red-500 mt-1">{importError}</p>
                )}
              </div>
              
              <Button 
                onClick={handleImport} 
                className="w-full"
                disabled={!file || isImporting}
              >
                {isImporting ? 'Importing...' : 'Import from JSON'}
              </Button>
            </div>
          </TabsContent>
        </Tabs>
        
        <DialogFooter>
          <div className="text-xs text-gray-500 mt-4">
            <p>Note: Importing data may overwrite existing records with the same ID.</p>
          </div>
        </DialogFooter>
      </DialogContent>
    </Dialog>
  );
}