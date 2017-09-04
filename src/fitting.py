import numpy as np
from scipy.signal import correlate2d
from scipy import optimize
from scipy.stats import pearsonr

import tools
import plot

def correlation_coef(Uw,Vw,u,v):
    Uw = Uw.ravel()
    Vw = Vw.ravel()
    u = u.ravel()
    v = v.ravel()
    N = Uw.size
    prod_PIV_mod = 0.0
    prod_PIV = 0.0
    prod_mod = 0.0
    for i in range(N):
        prod_PIV_mod += (Uw[i]*u[i]+Vw[i]*v[i])/N
        prod_PIV += (u[i]*u[i]+v[i]*v[i])/N
        prod_mod += (Uw[i]*Uw[i]+Vw[i]*Vw[i])/N
    upper = prod_PIV_mod
    lower = np.sqrt(prod_PIV)*np.sqrt(prod_mod)
    corr = np.sqrt(upper/lower)

    return corr

def velocity_model(coreR, gamma, fxCenter,fyCenter, u_conv, v_conv,x,y):
    r = np.hypot(x-fxCenter, y-fyCenter)
    vel = (gamma/(2 * np.pi * r)) * (1 - np.exp(-(r**2)/(coreR)**2))
    vel = np.nan_to_num(vel)
    velx = u_conv -vel*(y-fyCenter)/r
    vely = v_conv +vel*(x-fxCenter)/r
    velx = np.nan_to_num(velx)
    vely = np.nan_to_num(vely)
    return velx, vely

def get_vortices(a,peaks,vorticity):
    b = list()
    vortices = list()
    for i in range(len(peaks[0])):
        xCenter = peaks[1][i]
        yCenter = peaks[0][i]
        print(i," Processing detected swirling at (x,y)",xCenter,yCenter)
        coreR = 2*(a.dx[5]-a.dx[4]) #ugly change someday
        gamma = vorticity[yCenter,xCenter]*np.pi*coreR**2
        b = full_fit(coreR, gamma, a, xCenter, yCenter)
        if (b[4] > 0.90):
            print("Accepted!")
            vortices.append(b)
    return vortices

def full_fit(coreR, gamma, a, xCenter, yCenter):
    model = [[],[],[],[],[],[]]
    model[0] = coreR
    model[1] = gamma
    model[2] = a.dx[xCenter]
    model[3] = a.dy[yCenter]
    dx = a.dx[5]-a.dx[4] #ugly
    dy = a.dy[5]-a.dy[4]
    corr = 0.0
    for i in range(5):
        rOld = model[0]
        dist = int(round(model[0]/dx,0)) + 1
        model[4] = a.u[yCenter, xCenter] #u_conv
        model[5] = a.v[yCenter, xCenter] #v_conv
        X, Y, Uw, Vw = tools.window(a,xCenter,yCenter,dist)
        model = fit(model[0], model[1], X, Y, model[2], model[3], Uw, Vw, model[4], model[5])
        if abs(model[0]/rOld -1) < 0.10:
            break
        uMod, vMod = velocity_model(model[0], model[1], model[2], model[3], model[4], model[5],X,Y)
        corr = correlation_coef(Uw,Vw,uMod,vMod)
        xCenter = int(round(model[2]/dx))
        yCenter = int(round(model[3]/dy))
        if xCenter >= a.u.shape[1]:
            xCenter = a.u.shape[1]-1
        if yCenter >= a.v.shape[0]:
            yCenter = a.v.shape[0]-1
            #if ((model[2]-x1)/r1) > 0.1:
                #print((model[2]-x1)/r1)
                #print("shall be removed! x")
                #corr = 0.0
            #if ((model[3]-y1)/r1) > 0.1:
                #print((model[3]-y1)/r1)
                #print("shall be removed! y")
                #corr = 0.0
    return model[2], model[3], model[1], model[0], corr, dist, model[4], model[5]

def fit(coreR, gamma, x, y, fxCenter, fyCenter, Uw, Vw, u_conv, v_conv):
    x = x.ravel()
    y = y.ravel()
    Uw = Uw.ravel()
    Vw = Vw.ravel()
    dx = x[1]-x[0]
    dy = dx
    def fun(fitted): #fitted[0]=coreR, fitted[1]=gamma, fitted[2]=fxCenter, fitted[3]=fyCenter, fitted[4]=u_conv, fitted[5]=v_conv
        r = np.hypot(x-fitted[2], y-fitted[3])
        expr2 = np.exp(-r**2/fitted[0]**2)
        z = fitted[1]/(2*np.pi*r) * (1 - expr2)
        z = np.nan_to_num(z)
        zx = fitted[4] -z*(y-fitted[3])/r -Uw
        zy = fitted[5] +z*(x-fitted[2])/r -Vw
        zx = np.nan_to_num(zx)
        zy = np.nan_to_num(zy)
        zt = np.append(zx,zy)
        return zt
    #improve the boundary for convection velocity
    if (gamma<0):
        bnds=([coreR/10,gamma*50,fxCenter-2*dx,fyCenter-2*dy,u_conv-abs(u_conv),v_conv-abs(v_conv)],
          [coreR*5,gamma/100,fxCenter+2*dx,fyCenter+2*dy,u_conv+abs(u_conv),v_conv+abs(v_conv)])
    if (gamma>0):
        bnds=([coreR/10,gamma/50,fxCenter-2*dx,fyCenter-2*dy,u_conv-abs(u_conv),v_conv-abs(v_conv)],
          [coreR*5,gamma*100,fxCenter+2*dx,fyCenter+2*dy,u_conv+abs(u_conv),v_conv+abs(u_conv)])
    #print(bnds)
    sol = optimize.least_squares(fun, [coreR,gamma,fxCenter,fyCenter,u_conv,v_conv],bounds=bnds)     
    #Levenberg
    #sol = optimize.least_squares(fun, [coreR,gamma,fxCenter,fyCenter,u_conv,v_conv],method='lm')
    return sol.x
