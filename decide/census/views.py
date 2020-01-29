from django.db.utils import IntegrityError
from django.core.exceptions import ObjectDoesNotExist
from django.shortcuts import get_object_or_404
from rest_framework import generics
from rest_framework.response import Response
from django.shortcuts import redirect, render
from rest_framework.status import (
        HTTP_201_CREATED as ST_201,
        HTTP_204_NO_CONTENT as ST_204,
        HTTP_400_BAD_REQUEST as ST_400,
        HTTP_401_UNAUTHORIZED as ST_401,
        HTTP_409_CONFLICT as ST_409
)

from base.perms import UserIsStaff
from .models import Census
from voting.models import Voting
from authentication.models import Voter
from census.serializer import CensusSerializer
from django.http import HttpResponse
from django.contrib import messages
import csv, io
import random


class CensusCreate(generics.ListCreateAPIView):
    permission_classes = (UserIsStaff,)

    def create(self, request, *args, **kwargs):
        voting_id = request.data.get('voting_id')
        voters = request.data.get('voters')
        try:
            for voter in voters:
                census = Census(voting_id=voting_id, voter_id=voter)
                census.save()
        except IntegrityError:
            return Response('Error try to create census', status=ST_409)
        return Response('Census created', status=ST_201)

    def list(self, request, *args, **kwargs):
        voting_id = request.GET.get('voting_id')
        voters = Census.objects.filter(voting_id=voting_id).values_list('voter_id', flat=True)
        return Response({'voters': voters})


class CensusDetail(generics.RetrieveDestroyAPIView):

    def destroy(self, request, voting_id, *args, **kwargs):
        voters = request.data.get('voters')
        census = Census.objects.filter(voting_id=voting_id, voter_id__in=voters)
        census.delete()
        return Response('Voters deleted from census', status=ST_204)

    def retrieve(self, request, voting_id, *args, **kwargs):
        voter = request.GET.get('voter_id')
        try:
            Census.objects.get(voting_id=voting_id, voter_id=voter)
        except ObjectDoesNotExist:
            return Response('Invalid voter', status=ST_401)
        return Response('Valid voter')



def list_census(request):

    census = Census.objects.all()
    votings = Voting.objects.all()

    return render(request,"main_index.html",{'census': census, 'votings':votings})


def edit_census(request):

    if request.user.is_staff:
        n_id = request.GET.get('id')
        census = get_object_or_404(Census,id=n_id)

        return render(request, 'edit_census.html',{'census': census})

def save_edited_census(request):
    if request.user.is_staff:
        census_id = request.GET.get('id')
        voting_id = request.GET.get('voting_id')
        voter_id = request.GET.get('voter_id')
        census = get_object_or_404(Census,id=census_id)

        census.voting_id = voting_id
        census.voter_id = voter_id
        census.save()

    else:
        messages.add_message(request, messages.ERROR, "Permission denied")

    return redirect('filterCensus')


def add_census(request):

    return render(request, 'add_census.html')

def save_new_census(request):
    if request.user.is_staff:
        census_id = request.GET.get('id')
        voting_id = request.GET.get('voting_id')
        voter_id = request.GET.get('voter_id')
        
        census = Census(voting_id=voting_id, voter_id=voter_id)
        census.save()
    else:
        messages.add_message(request, messages.ERROR, "Permission denied")

    return redirect('filterCensus')

def delete_census(request):
    if request.user.is_staff:
        n_id = request.GET.get('id')
        census = get_object_or_404(Census,id=n_id)

        return render(request, 'delete_census.html',{'census': census})
    else:
        messages.add_message(request, messages.ERROR, "Permission denied")

        return redirect('listCensus')

def delete_selected_census(request):

    if request.user.is_staff:
        census_id = request.GET.get('id')
        census = get_object_or_404(Census,id=census_id)
        census.delete()

    else:
        messages.add_message(request, messages.ERROR, "Permission denied")
    return redirect('listCensus')
    
    
def view_voting(request):
    if request.user.is_staff:
        n_id = request.GET.get('id')
        census = get_object_or_404(Census,id=n_id)
        voters = []
        
        voters = get_voters_by_voting_id(voting_id=census.voting_id)

        return render(request, 'view_voting.html',{'census': census ,'voting_id': census.voting_id, 'voters': voters})
    
def get_voters_by_voting_id(voting_id):
    allCensus = Census.objects.all()
    votingSelected_id = voting_id
    voters = []
    
    for cens in allCensus:
        if cens.voting_id == votingSelected_id:
            voters.append(cens.voter_id)
    
    return voters
    
def move_voters_view(request):
    if request.user.is_staff:
        census_id = request.GET.get('id')
        census = get_object_or_404(Census,id=census_id)
        voters = []
        voters = get_voters_by_voting_id(voting_id=census.voting_id)
        votings = []
        for cens in Census.objects.all():
            if cens.voting_id not in votings:
                votings.append(cens.voting_id)
        
        return render(request, 'move_voters.html',{'census': census, 'voting_id': census.voting_id, 'voters': voters, 'votings': votings})     

def move_voters(request):
    census_id = request.GET.get('id')
    votings = request.GET.get('votings')
    voting_id = request.GET.get('voting_id')
    
    allCensus = Census.objects.all()
    census = get_object_or_404(Census,id=census_id)
    if voting_id == '' or int(voting_id) == census.voting_id:
        return redirect('listCensus')
    voters = []
    voters = get_voters_by_voting_id(voting_id=int(voting_id))
    votersToMove = []
    votersToMove = get_voters_by_voting_id(voting_id=census.voting_id)
    
    for voter in votersToMove:
        if voting_id in votings:
            if voter not in voters:
                newCensus = Census(voting_id= voting_id, voter_id=voter)
                newCensus.save()
        else:
                newCensus = Census(voting_id= voting_id, voter_id= voter)
                newCensus.save()
    return redirect('listCensus')    
        

def exportCSV(request):
    res = HttpResponse(content_type='text/csv')
    res['Content-Disposition'] = 'attachment; filename="census.csv"'

    censo = Census.objects.all()
    datos = [field.attname for field in Census._meta.get_fields()]

    w = csv.writer(res)
    w.writerow(datos)

    for c in censo:
        w.writerow([c.id, c.voting_id, c.voter_id])
    
    return res
 
def import_csv(request):
    if request.user.is_staff:
        if 'file' in request.FILES:
            file = request.FILES['file']
            data_set =  file.read().decode('utf-8-sig')
            arr = data_set.strip().split("\n") 
            contador = 0
            for e in arr:
                if contador == 0:
                    contador = contador + 1
                else:
                    numbers = e.replace("\r", "").split(",")
                    census = Census(voting_id=numbers[1], voter_id=numbers[2])
                    census.save()
                    print(numbers)
                    contador = contador + 1
    else:
        messages.add_message(request, messages.ERROR, "Permission denied")
    
    return redirect('listCensus')

def import_csv_view(request):
    if request.user.is_staff:
        return render(request, "import_csv.html")

    else:
       messages.add_message(request, messages.ERROR, "Permission denied") 
       return redirect('listCensus')

# Introducción del código postal

def add_census_CP(request):

    return render(request, 'add_census_CP.html')

voting_id_global= 0

def save_new_census_CP(request):
    global voting_id_global
    voting_id_global = voting_id_global + 1
    voters = Voter.objects.all()
    census = Census.objects.all()
    postal_code_introducido = int(request.GET.get('postal_code'))
    list_postal_code_all = []
    list_postal_code = []
    for vo in voters:
        list_postal_code_all.append(vo.postal_code)
    for cens in census: 
        voter_id_cens = cens.voter_id
        for vot in voters:
            if voter_id_cens == vot.id:
                list_postal_code.append(vot.postal_code)

    if postal_code_introducido in list_postal_code:
        return redirect('error1')
    elif not(postal_code_introducido in list_postal_code_all):
        return redirect('error2')
    else:
        if request.user.is_staff:
            for v in voters:
                voter_id = v.id
                postal_code = v.postal_code
                if v.postal_code != None:
                    if postal_code == postal_code_introducido:
                        voting_id = voting_id_global
                        census_id = request.GET.get('id')
                        census = Census(voting_id=voting_id, voter_id=voter_id)
                        census.save()
                

        else:
            messages.add_message(request, messages.ERROR, "Permission denied")

        return redirect('listCensusCP')

def list_census_CP(request):

    censusAll = Census.objects.all()
    census = sorted(censusAll, key=lambda objeto: objeto.voting_id)

    return render(request,"list_census_CP_main.html",{'census': census})

def error_1(request):

    return render(request,"error1.html")

def error_2(request):
    return render(request,"error2.html")

def filter(request):
    census = Census.objects.all()
    conj = set()
    nodraft = set()
    for i in census:
        id = i.voting_id
        conj.add(id)
        if id != 0:
            nodraft.add(id)

    return render(request,"filter_census.html",{'census': census,'conj':conj,'nodraft':nodraft})

def deleteAll(request):
    census = Census.objects.all()
    for cens in census:
        cens.delete()
    return redirect('filterCensus')      

