// Dump Ghidra functions and basic sizes to CSV.
// Usage: -postScript DumpFunctions.java <output.csv>
import ghidra.app.script.GhidraScript;
import ghidra.program.model.listing.Function;
import ghidra.program.model.listing.FunctionManager;
import java.io.File;
import java.io.PrintWriter;

public class DumpFunctions extends GhidraScript {
    @Override
    public void run() throws Exception {
        String[] args = getScriptArgs();
        File out = new File(args.length > 0 ? args[0] : "functions.csv");
        File parent = out.getParentFile();
        if (parent != null && !parent.exists()) {
            parent.mkdirs();
        }
        try (PrintWriter w = new PrintWriter(out, "UTF-8")) {
            w.println("address,name,size,thunk,external");
            FunctionManager fm = currentProgram.getFunctionManager();
            for (Function f : fm.getFunctions(true)) {
                String name = f.getName().replace(",", "_");
                w.println(f.getEntryPoint() + "," + name + "," + f.getBody().getNumAddresses()
                        + "," + f.isThunk() + "," + f.isExternal());
            }
        }
        println("DumpFunctions wrote " + out.getAbsolutePath());
    }
}
