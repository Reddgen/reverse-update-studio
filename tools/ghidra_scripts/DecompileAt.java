// Decompile selected addresses to C-like pseudocode.
// Usage: -postScript DecompileAt.java <addresses.txt> <output-dir>
import ghidra.app.decompiler.DecompInterface;
import ghidra.app.decompiler.DecompileResults;
import ghidra.app.script.GhidraScript;
import ghidra.program.model.address.Address;
import ghidra.program.model.listing.Function;
import ghidra.program.model.listing.FunctionManager;
import java.io.BufferedReader;
import java.io.File;
import java.io.FileReader;
import java.io.PrintWriter;

public class DecompileAt extends GhidraScript {
    private static String safe(String s) {
        return s.replaceAll("[^A-Za-z0-9_.-]+", "_");
    }

    @Override
    public void run() throws Exception {
        String[] args = getScriptArgs();
        if (args.length < 2) {
            println("usage: DecompileAt.java <addresses.txt> <output-dir>");
            return;
        }
        File addressFile = new File(args[0]);
        File outDir = new File(args[1]);
        if (!outDir.exists()) {
            outDir.mkdirs();
        }
        DecompInterface ifc = new DecompInterface();
        ifc.openProgram(currentProgram);
        FunctionManager fm = currentProgram.getFunctionManager();
        File index = new File(outDir, "index.csv");
        try (BufferedReader r = new BufferedReader(new FileReader(addressFile));
             PrintWriter idx = new PrintWriter(index, "UTF-8")) {
            idx.println("requested,function,size,ok,file,error");
            String line;
            while ((line = r.readLine()) != null) {
                line = line.trim();
                if (line.isEmpty() || line.startsWith("#")) {
                    continue;
                }
                String requested = line.split("[\\s,]+")[0];
                Address addr;
                try {
                    addr = toAddr(requested);
                } catch (Exception e) {
                    idx.println(requested + ",,,false,," + safe(e.toString()));
                    continue;
                }
                Function f = fm.getFunctionAt(addr);
                if (f == null) {
                    f = fm.getFunctionContaining(addr);
                }
                if (f == null) {
                    idx.println(requested + ",,,false,,no function");
                    continue;
                }
                String base = requested + "_" + safe(f.getName());
                File out = new File(outDir, base + ".c");
                String error = "";
                boolean ok = false;
                try {
                    DecompileResults res = ifc.decompileFunction(f, 90, monitor);
                    if (res != null && res.decompileCompleted() && res.getDecompiledFunction() != null) {
                        try (PrintWriter w = new PrintWriter(out, "UTF-8")) {
                            w.println("// requested: " + requested);
                            w.println("// function:  " + f.getName());
                            w.println("// entry:     " + f.getEntryPoint());
                            w.println("// size:      " + f.getBody().getNumAddresses());
                            w.println();
                            w.print(res.getDecompiledFunction().getC());
                        }
                        ok = true;
                    } else {
                        error = res == null ? "null result" : res.getErrorMessage();
                    }
                } catch (Exception e) {
                    error = e.toString();
                }
                idx.println(requested + "," + f.getName() + "," + f.getBody().getNumAddresses()
                        + "," + ok + "," + (ok ? out.getName() : "") + "," + safe(error));
                println("DecompileAt " + requested + " -> " + f.getName() + " ok=" + ok);
            }
        } finally {
            ifc.dispose();
        }
        println("DecompileAt wrote " + index.getAbsolutePath());
    }
}
